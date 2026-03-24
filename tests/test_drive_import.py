"""Tests for Google Drive media import endpoints."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from api.models import Base, MediaCatalog


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
    monkeypatch.setenv("GOOGLE_DRIVE_FOLDER_ID", "test-folder-id")
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


MOCK_DRIVE_FILES = {
    "files": [
        {
            "id": "drive-file-1",
            "name": "temple-photo.jpg",
            "mimeType": "image/jpeg",
            "size": "250000",
            "thumbnailLink": "https://drive.google.com/thumb/1",
        },
        {
            "id": "drive-file-2",
            "name": "farm-cows.png",
            "mimeType": "image/png",
            "size": "500000",
            "thumbnailLink": "https://drive.google.com/thumb/2",
        },
    ],
    "nextPageToken": None,
}


class TestDriveBrowse:
    @patch("api.routes.drive.get_drive_service")
    def test_browse_returns_files(self, mock_service, client, auth_headers):
        mock_files = MagicMock()
        mock_files.list.return_value.execute.return_value = MOCK_DRIVE_FILES
        mock_service.return_value.files.return_value = mock_files

        resp = client.get(
            "/api/media/drive/browse?folder_id=test-folder",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["files"]) == 2
        assert data["files"][0]["name"] == "temple-photo.jpg"

    @patch("api.routes.drive.get_drive_service")
    def test_browse_with_page_token(self, mock_service, client, auth_headers):
        mock_files = MagicMock()
        mock_files.list.return_value.execute.return_value = {
            "files": [],
            "nextPageToken": "token123",
        }
        mock_service.return_value.files.return_value = mock_files

        resp = client.get(
            "/api/media/drive/browse?folder_id=test-folder&page_token=prev-token",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["next_page_token"] == "token123"

    @patch("api.routes.drive.get_drive_service")
    def test_browse_service_error(self, mock_service, client, auth_headers):
        mock_service.side_effect = Exception("No credentials")
        resp = client.get(
            "/api/media/drive/browse?folder_id=test-folder",
            headers=auth_headers,
        )
        assert resp.status_code == 500


class TestDriveImport:
    @patch("api.routes.drive._download_drive_file")
    @patch("api.routes.drive.get_drive_service")
    @patch("api.routes.media._classify_media_tags")
    @patch("api.routes.media._upload_to_postiz")
    def test_import_creates_catalog_entries(
        self,
        mock_postiz,
        mock_tags,
        mock_service,
        mock_download,
        client,
        auth_headers,
        db_engine,
    ):
        mock_postiz.return_value = None
        mock_tags.return_value = [{"tag": "temple", "confidence": 0.9}]

        # Mock Drive file metadata
        mock_files = MagicMock()
        mock_files.get.return_value.execute.return_value = {
            "id": "drive-file-1",
            "name": "temple.jpg",
            "mimeType": "image/jpeg",
            "size": "50000",
        }
        mock_service.return_value.files.return_value = mock_files

        # Create a minimal JPEG for download mock
        import io

        from PIL import Image

        img = Image.new("RGB", (800, 600))
        buf = io.BytesIO()
        img.save(buf, "JPEG")
        mock_download.return_value = buf.getvalue()

        resp = client.post(
            "/api/media/import-drive",
            json={"file_ids": ["drive-file-1"]},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["imported"] == 1
        assert len(data["errors"]) == 0

    @patch("api.routes.drive._download_drive_file")
    @patch("api.routes.drive.get_drive_service")
    @patch("api.routes.media._classify_media_tags")
    @patch("api.routes.media._upload_to_postiz")
    def test_import_skips_already_imported(
        self,
        mock_postiz,
        mock_tags,
        mock_service,
        mock_download,
        client,
        auth_headers,
        db_engine,
    ):
        mock_postiz.return_value = None
        mock_tags.return_value = []

        # Seed existing media with same drive file ID
        with Session(db_engine) as s:
            s.add(
                MediaCatalog(
                    filename="existing.jpg",
                    local_path="media/existing.jpg",
                    mime_type="image/jpeg",
                    file_size=50000,
                    source="drive",
                    original_url="drive://drive-file-1",
                )
            )
            s.commit()

        resp = client.post(
            "/api/media/import-drive",
            json={"file_ids": ["drive-file-1"]},
            headers=auth_headers,
        )
        data = resp.json()
        assert data["imported"] == 0
        assert len(data["skipped"]) == 1

    def test_import_empty_list(self, client, auth_headers):
        resp = client.post(
            "/api/media/import-drive",
            json={"file_ids": []},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["imported"] == 0
