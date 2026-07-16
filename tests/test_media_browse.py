"""Tests for media browse, search, detail, tagging, and delete endpoints."""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from api.models import (
    Base,
    ContentRow,
    MediaCatalog,
    MediaPerformance,
    MediaTag,
)


@pytest.fixture(autouse=True)
def _clear_caches():
    import api.dependencies as deps
    from api.dependencies import get_settings

    get_settings.cache_clear()
    deps._engine = None
    deps._session_factory = None
    yield
    get_settings.cache_clear()
    deps._engine = None
    deps._session_factory = None


@pytest.fixture
def _env_vars(monkeypatch, tmp_path):
    monkeypatch.setenv("JWT_SECRET", "test-secret-key-min-32-chars-long!!")
    monkeypatch.setenv("API_PASSWORD", "testpass")
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("POSTIZ_API_KEY", "test-key")
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    engine.dispose()


@pytest.fixture
def db_engine(_env_vars, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    yield engine
    engine.dispose()


@pytest.fixture
def client(_env_vars):
    from api.main import app

    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    resp = client.post("/api/auth/login", json={"password": "testpass"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _seed_media(engine, count=5, **overrides):
    """Insert test media rows and return their IDs."""
    ids = []
    with Session(engine) as session:
        for i in range(count):
            m = MediaCatalog(
                filename=overrides.get("filename", f"photo_{i}.jpg"),
                local_path=overrides.get("local_path", f"media/{i}.jpg"),
                thumbnail_path=overrides.get("thumbnail_path", f"media/thumbnails/thumb_{i}.jpg"),
                mime_type=overrides.get("mime_type", "image/jpeg"),
                width=overrides.get("width", 800),
                height=overrides.get("height", 600),
                file_size=overrides.get("file_size", 50000),
                source=overrides.get("source", "upload"),
                pillar=overrides.get("pillar"),
                usage_count=overrides.get("usage_count", 0),
                avg_engagement=overrides.get("avg_engagement", 0.0),
                tags=json.dumps(overrides.get("tag_list", ["farm", "outdoor"])),
            )
            session.add(m)
            session.flush()
            ids.append(m.id)
        session.commit()
    return ids


def _seed_tags(engine, media_id, tags):
    """Insert MediaTag rows for a media item."""
    with Session(engine) as session:
        for t in tags:
            session.add(
                MediaTag(
                    media_id=media_id,
                    tag=t["tag"],
                    confidence=t.get("confidence", 0.8),
                    source=t.get("source", "ai"),
                )
            )
        session.commit()


def _seed_performance(engine, media_id, records):
    """Insert MediaPerformance rows."""
    with Session(engine) as session:
        for r in records:
            session.add(
                MediaPerformance(
                    media_id=media_id,
                    platform=r["platform"],
                    engagement_score=r.get("engagement_score", 0.0),
                    content_row_id=r.get("content_row_id"),
                )
            )
        session.commit()


def _seed_content_row(engine, **overrides):
    """Insert a content row and return its ID."""
    with Session(engine) as session:
        row = ContentRow(
            raw_text=overrides.get("raw_text", "Test post"),
            status=overrides.get("status", "draft"),
            pillar=overrides.get("pillar", "spiritual_education"),
            media_catalog_ids=overrides.get("media_catalog_ids"),
            platforms=json.dumps(overrides.get("platforms", {"facebook": True})),
            captions=json.dumps(overrides.get("captions", {"facebook": "test"})),
        )
        session.add(row)
        session.flush()
        row_id = row.id
        session.commit()
    return row_id


# ── Browse (GET /api/media) ────────────────────────────────────────────


class TestMediaBrowse:
    def test_browse_returns_paginated_results(self, client, auth_headers, db_engine):
        _seed_media(db_engine, count=15)
        resp = client.get("/api/media", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1
        assert data["per_page"] == 20
        assert data["total"] == 15
        assert data["total_pages"] == 1
        assert len(data["items"]) == 15

    def test_browse_pagination(self, client, auth_headers, db_engine):
        _seed_media(db_engine, count=25)
        resp = client.get("/api/media?page=2&per_page=10", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 2
        assert data["per_page"] == 10
        assert data["total"] == 25
        assert data["total_pages"] == 3
        assert len(data["items"]) == 10

    def test_browse_last_page(self, client, auth_headers, db_engine):
        _seed_media(db_engine, count=25)
        resp = client.get("/api/media?page=3&per_page=10", headers=auth_headers)
        data = resp.json()
        assert len(data["items"]) == 5

    def test_browse_filter_by_source(self, client, auth_headers, db_engine):
        _seed_media(db_engine, count=3, source="upload")
        _seed_media(db_engine, count=2, source="import_url")
        resp = client.get("/api/media?source=upload", headers=auth_headers)
        data = resp.json()
        assert data["total"] == 3

    def test_browse_filter_by_pillar(self, client, auth_headers, db_engine):
        _seed_media(db_engine, count=4, pillar="spiritual_education")
        _seed_media(db_engine, count=2, pillar="farm_life")
        resp = client.get("/api/media?pillar=farm_life", headers=auth_headers)
        data = resp.json()
        assert data["total"] == 2

    def test_browse_filter_by_tag(self, client, auth_headers, db_engine):
        ids = _seed_media(db_engine, count=3)
        _seed_tags(db_engine, ids[0], [{"tag": "cows"}])
        _seed_tags(db_engine, ids[1], [{"tag": "cows"}, {"tag": "farm"}])
        _seed_tags(db_engine, ids[2], [{"tag": "kitchen"}])
        resp = client.get("/api/media?tag=cows", headers=auth_headers)
        data = resp.json()
        assert data["total"] == 2

    def test_browse_sort_by_engagement(self, client, auth_headers, db_engine):
        _seed_media(db_engine, count=1, avg_engagement=0.5, filename="low.jpg")
        _seed_media(db_engine, count=1, avg_engagement=0.9, filename="high.jpg")
        resp = client.get("/api/media?sort=engagement", headers=auth_headers)
        data = resp.json()
        assert data["items"][0]["avg_engagement"] >= data["items"][1]["avg_engagement"]

    def test_browse_sort_by_usage(self, client, auth_headers, db_engine):
        _seed_media(db_engine, count=1, usage_count=10, filename="popular.jpg")
        _seed_media(db_engine, count=1, usage_count=1, filename="rare.jpg")
        resp = client.get("/api/media?sort=usage_count", headers=auth_headers)
        data = resp.json()
        assert data["items"][0]["usage_count"] >= data["items"][1]["usage_count"]

    def test_browse_empty_catalog(self, client, auth_headers):
        resp = client.get("/api/media", headers=auth_headers)
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_browse_requires_auth(self, client):
        resp = client.get("/api/media")
        assert resp.status_code == 401


# ── Detail (GET /api/media/{id}) ────────────────────────────────────────


class TestMediaDetail:
    def test_detail_returns_media_with_tags(self, client, auth_headers, db_engine):
        ids = _seed_media(db_engine, count=1)
        _seed_tags(
            db_engine,
            ids[0],
            [{"tag": "outdoor", "confidence": 0.9}, {"tag": "farm", "confidence": 0.7}],
        )
        resp = client.get(f"/api/media/{ids[0]}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["media"]["id"] == ids[0]
        assert len(data["tags"]) == 2
        assert data["tags"][0]["tag"] in ("outdoor", "farm")

    def test_detail_includes_usage_history(self, client, auth_headers, db_engine):
        ids = _seed_media(db_engine, count=1)
        cr_id = _seed_content_row(db_engine, media_catalog_ids=json.dumps([ids[0]]))
        resp = client.get(f"/api/media/{ids[0]}", headers=auth_headers)
        data = resp.json()
        assert len(data["usage"]) == 1
        assert data["usage"][0]["content_row_id"] == cr_id

    def test_detail_includes_performance(self, client, auth_headers, db_engine):
        ids = _seed_media(db_engine, count=1)
        _seed_performance(
            db_engine,
            ids[0],
            [{"platform": "facebook", "engagement_score": 0.85}],
        )
        resp = client.get(f"/api/media/{ids[0]}", headers=auth_headers)
        data = resp.json()
        assert len(data["performance"]) == 1
        assert data["performance"][0]["platform"] == "facebook"

    def test_detail_not_found(self, client, auth_headers):
        resp = client.get("/api/media/9999", headers=auth_headers)
        assert resp.status_code == 404


# ── Tag Management (PUT /api/media/{id}/tags) ──────────────────────────


class TestMediaTagManagement:
    def test_add_tags(self, client, auth_headers, db_engine):
        ids = _seed_media(db_engine, count=1)
        resp = client.put(
            f"/api/media/{ids[0]}/tags",
            json={"add": ["cows", "landscape"], "remove": []},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        tag_names = [t["tag"] for t in data["tags"]]
        assert "cows" in tag_names
        assert "landscape" in tag_names

    def test_add_tags_manual_source(self, client, auth_headers, db_engine):
        ids = _seed_media(db_engine, count=1)
        resp = client.put(
            f"/api/media/{ids[0]}/tags",
            json={"add": ["deity"], "remove": []},
            headers=auth_headers,
        )
        data = resp.json()
        deity_tag = next(t for t in data["tags"] if t["tag"] == "deity")
        assert deity_tag["source"] == "manual"
        assert deity_tag["confidence"] == 1.0

    def test_remove_tags(self, client, auth_headers, db_engine):
        ids = _seed_media(db_engine, count=1)
        _seed_tags(db_engine, ids[0], [{"tag": "outdoor"}, {"tag": "farm"}])
        resp = client.put(
            f"/api/media/{ids[0]}/tags",
            json={"add": [], "remove": ["outdoor"]},
            headers=auth_headers,
        )
        data = resp.json()
        tag_names = [t["tag"] for t in data["tags"]]
        assert "outdoor" not in tag_names
        assert "farm" in tag_names

    def test_add_and_remove_tags(self, client, auth_headers, db_engine):
        ids = _seed_media(db_engine, count=1)
        _seed_tags(db_engine, ids[0], [{"tag": "old_tag"}])
        resp = client.put(
            f"/api/media/{ids[0]}/tags",
            json={"add": ["new_tag"], "remove": ["old_tag"]},
            headers=auth_headers,
        )
        data = resp.json()
        tag_names = [t["tag"] for t in data["tags"]]
        assert "new_tag" in tag_names
        assert "old_tag" not in tag_names

    def test_add_duplicate_tag_idempotent(self, client, auth_headers, db_engine):
        ids = _seed_media(db_engine, count=1)
        _seed_tags(db_engine, ids[0], [{"tag": "farm"}])
        resp = client.put(
            f"/api/media/{ids[0]}/tags",
            json={"add": ["farm"], "remove": []},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        farm_tags = [t for t in data["tags"] if t["tag"] == "farm"]
        assert len(farm_tags) == 1

    def test_tags_not_found(self, client, auth_headers):
        resp = client.put(
            "/api/media/9999/tags",
            json={"add": ["test"], "remove": []},
            headers=auth_headers,
        )
        assert resp.status_code == 404


# ── Delete (DELETE /api/media/{id}) ────────────────────────────────────


class TestMediaDelete:
    def test_delete_media(self, client, auth_headers, db_engine, tmp_path):
        # Create actual files so delete can clean up
        media_dir = tmp_path / "media"
        media_dir.mkdir()
        (media_dir / "thumbnails").mkdir()
        file_path = media_dir / "test.jpg"
        file_path.write_bytes(b"fake image content")
        thumb_path = media_dir / "thumbnails" / "thumb_test.jpg"
        thumb_path.write_bytes(b"fake thumb")

        with Session(db_engine) as session:
            m = MediaCatalog(
                filename="test.jpg",
                local_path=str(file_path),
                thumbnail_path=str(thumb_path),
                mime_type="image/jpeg",
                file_size=100,
                source="upload",
            )
            session.add(m)
            session.flush()
            media_id = m.id
            session.commit()

        resp = client.delete(f"/api/media/{media_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

        # Files should be cleaned up
        assert not file_path.exists()
        assert not thumb_path.exists()

    def test_delete_removes_related_tags(self, client, auth_headers, db_engine):
        ids = _seed_media(db_engine, count=1)
        _seed_tags(db_engine, ids[0], [{"tag": "farm"}, {"tag": "outdoor"}])
        resp = client.delete(f"/api/media/{ids[0]}", headers=auth_headers)
        assert resp.status_code == 200

        # Verify tags removed from DB
        with Session(db_engine) as session:
            from sqlalchemy import select

            tags = (
                session.execute(select(MediaTag).where(MediaTag.media_id == ids[0])).scalars().all()
            )
            assert len(tags) == 0

    def test_delete_not_found(self, client, auth_headers):
        resp = client.delete("/api/media/9999", headers=auth_headers)
        assert resp.status_code == 404

    def test_delete_handles_missing_files(self, client, auth_headers, db_engine):
        """Delete should succeed even if local files are already gone."""
        ids = _seed_media(db_engine, count=1, local_path="/nonexistent/file.jpg")
        resp = client.delete(f"/api/media/{ids[0]}", headers=auth_headers)
        assert resp.status_code == 200


# ── Phase 3 browse params (q, media_type, untagged, storage_used_bytes) ──


class TestMediaBrowsePhase3:
    def test_q_matches_filename_case_insensitive(self, client, auth_headers, db_engine):
        _seed_media(db_engine, count=1, filename="Sunset_Pasture.jpg")
        _seed_media(db_engine, count=1, filename="kitchen.jpg")
        resp = client.get("/api/media?q=PASTURE", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["filename"] == "Sunset_Pasture.jpg"

    def test_q_matches_tag(self, client, auth_headers, db_engine):
        ids = _seed_media(db_engine, count=2)
        _seed_tags(db_engine, ids[0], [{"tag": "deity"}])
        _seed_tags(db_engine, ids[1], [{"tag": "kitchen"}])
        resp = client.get("/api/media?q=DEI", headers=auth_headers)
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == ids[0]

    def test_q_matches_filename_or_tag(self, client, auth_headers, db_engine):
        ids = _seed_media(db_engine, count=1, filename="cows_field.jpg")
        other = _seed_media(db_engine, count=1, filename="building.jpg")
        _seed_tags(db_engine, other[0], [{"tag": "cows"}])
        resp = client.get("/api/media?q=cows", headers=auth_headers)
        data = resp.json()
        assert data["total"] == 2
        found = {i["id"] for i in data["items"]}
        assert found == {ids[0], other[0]}

    def test_q_no_match(self, client, auth_headers, db_engine):
        _seed_media(db_engine, count=2)
        resp = client.get("/api/media?q=zzzznotthere", headers=auth_headers)
        assert resp.json()["total"] == 0

    def test_q_underscore_is_literal(self, client, auth_headers, db_engine):
        """'_' in q must not act as a single-char wildcard."""
        _seed_media(db_engine, count=1, filename="a_b.jpg")
        _seed_media(db_engine, count=1, filename="axb.jpg")
        resp = client.get("/api/media", params={"q": "a_b"}, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["filename"] == "a_b.jpg"

    def test_q_percent_matches_only_literal_percent(self, client, auth_headers, db_engine):
        """'%' in q must not match everything — only literal '%' occurrences."""
        _seed_media(db_engine, count=1, filename="sale_100%.jpg")
        _seed_media(db_engine, count=1, filename="normal.jpg")
        resp = client.get("/api/media", params={"q": "%"}, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["filename"] == "sale_100%.jpg"

    def test_q_percent_matches_literal_in_tag(self, client, auth_headers, db_engine):
        """Escaping applies to the tag branch too, not just filenames."""
        ids = _seed_media(db_engine, count=2)
        _seed_tags(db_engine, ids[0], [{"tag": "50%off"}])
        _seed_tags(db_engine, ids[1], [{"tag": "plain"}])
        resp = client.get("/api/media", params={"q": "%"}, headers=auth_headers)
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == ids[0]

    def test_q_100_percent_literal(self, client, auth_headers, db_engine):
        """q='100%' matches literal '100%', not any string containing '100'."""
        _seed_media(db_engine, count=1, filename="sale_100%.jpg")
        _seed_media(db_engine, count=1, filename="100days.jpg")
        resp = client.get("/api/media", params={"q": "100%"}, headers=auth_headers)
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["filename"] == "sale_100%.jpg"

    def test_q_backslash_literal(self, client, auth_headers, db_engine):
        """Backslash in q is escaped, not treated as an escape char itself."""
        _seed_media(db_engine, count=1, filename="back\\slash.jpg")
        _seed_media(db_engine, count=1, filename="backslash.jpg")
        resp = client.get("/api/media", params={"q": "back\\slash"}, headers=auth_headers)
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["filename"] == "back\\slash.jpg"

    def test_media_type_image(self, client, auth_headers, db_engine):
        _seed_media(db_engine, count=2, mime_type="image/jpeg")
        _seed_media(db_engine, count=1, mime_type="video/mp4", filename="clip.mp4")
        resp = client.get("/api/media?media_type=image", headers=auth_headers)
        data = resp.json()
        assert data["total"] == 2

    def test_media_type_video(self, client, auth_headers, db_engine):
        _seed_media(db_engine, count=2, mime_type="image/jpeg")
        _seed_media(db_engine, count=1, mime_type="video/mp4", filename="clip.mp4")
        resp = client.get("/api/media?media_type=video", headers=auth_headers)
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["mime_type"] == "video/mp4"

    def test_media_type_invalid_422(self, client, auth_headers):
        resp = client.get("/api/media?media_type=audio", headers=auth_headers)
        assert resp.status_code == 422

    def test_untagged_filter(self, client, auth_headers, db_engine):
        ids = _seed_media(db_engine, count=3)
        _seed_tags(db_engine, ids[0], [{"tag": "farm"}])
        resp = client.get("/api/media?untagged=true", headers=auth_headers)
        data = resp.json()
        assert data["total"] == 2
        found = {i["id"] for i in data["items"]}
        assert ids[0] not in found

    def test_untagged_default_false(self, client, auth_headers, db_engine):
        ids = _seed_media(db_engine, count=2)
        _seed_tags(db_engine, ids[0], [{"tag": "farm"}])
        resp = client.get("/api/media", headers=auth_headers)
        assert resp.json()["total"] == 2

    def test_combined_filters_and_semantics(self, client, auth_headers, db_engine):
        ids = _seed_media(db_engine, count=1, filename="cows.jpg", mime_type="image/jpeg")
        _seed_media(db_engine, count=1, filename="cows.mp4", mime_type="video/mp4")
        resp = client.get("/api/media?q=cows&media_type=image", headers=auth_headers)
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == ids[0]

    def test_storage_used_bytes_entire_catalog(self, client, auth_headers, db_engine):
        _seed_media(db_engine, count=2, file_size=100, source="upload")
        _seed_media(db_engine, count=1, file_size=50, source="import_url")
        # Filtered browse still reports storage for the ENTIRE catalog
        resp = client.get("/api/media?source=upload", headers=auth_headers)
        data = resp.json()
        assert data["total"] == 2
        assert data["storage_used_bytes"] == 250

    def test_storage_used_bytes_null_file_size_counts_zero(self, client, auth_headers, db_engine):
        _seed_media(db_engine, count=1, file_size=100)
        _seed_media(db_engine, count=1, file_size=None)
        resp = client.get("/api/media", headers=auth_headers)
        assert resp.json()["storage_used_bytes"] == 100

    def test_storage_used_bytes_empty_catalog(self, client, auth_headers):
        resp = client.get("/api/media", headers=auth_headers)
        assert resp.json()["storage_used_bytes"] == 0
