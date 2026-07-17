"""Tests for the public media URL resolver (api/services/media_public.py).

Postiz downloads media server-side, so publish paths must hand it a URL
reachable from the public internet. The resolver maps a content row's
media to such a URL (ensuring an anyone-with-link reader permission for
Google Drive files on the way) or raises MediaNotPublicError for
local-only media.
"""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.models import Base, MediaCatalog
from api.services.media_public import MediaNotPublicError, resolve_public_media_url


def make_row(media_url=None, media_catalog_ids=None):
    """Minimal row stand-in: the resolver reads only these two fields."""
    return SimpleNamespace(media_url=media_url, media_catalog_ids=media_catalog_ids)


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def drive_service(monkeypatch):
    """Mock Drive API service; records permissions().create(...) calls."""
    service = MagicMock()
    service.permissions.return_value.create.return_value.execute.return_value = {"id": "perm-1"}
    monkeypatch.setattr("api.routes.drive.get_drive_service", lambda: service)
    return service


def permission_create_kwargs(drive_service):
    return drive_service.permissions.return_value.create.call_args.kwargs


@pytest.mark.asyncio
class TestHttpPassthrough:
    async def test_https_url_returned_as_is(self):
        row = make_row(media_url="https://example.com/a.jpg")
        assert await resolve_public_media_url(None, row) == "https://example.com/a.jpg"

    async def test_http_url_returned_as_is(self):
        row = make_row(media_url="http://example.com/a.jpg")
        assert await resolve_public_media_url(None, row) == "http://example.com/a.jpg"

    async def test_drive_sharing_url_returned_as_is(self):
        """Full Drive URLs pass through — PostizClient normalizes them."""
        url = "https://drive.google.com/file/d/abc123/view"
        assert await resolve_public_media_url(None, make_row(media_url=url)) == url


@pytest.mark.asyncio
class TestNoMedia:
    async def test_no_media_returns_none(self):
        assert await resolve_public_media_url(None, make_row()) is None

    async def test_empty_catalog_list_returns_none(self):
        row = make_row(media_catalog_ids="[]")
        assert await resolve_public_media_url(None, row) is None


@pytest.mark.asyncio
class TestDriveProxyUrl:
    async def test_grants_permission_and_returns_direct_url(self, drive_service):
        row = make_row(media_url="/api/media/drive/file/abc-123_XY")
        url = await resolve_public_media_url(None, row)
        assert url == "https://drive.google.com/uc?export=download&id=abc-123_XY"
        kwargs = permission_create_kwargs(drive_service)
        assert kwargs["fileId"] == "abc-123_XY"
        assert kwargs["body"] == {"type": "anyone", "role": "reader"}

    async def test_permission_already_exists_is_swallowed(self, drive_service):
        drive_service.permissions.return_value.create.return_value.execute.side_effect = Exception(
            "The permission already exists on this file"
        )
        url = await resolve_public_media_url(None, make_row(media_url="/api/media/drive/file/f1"))
        assert url == "https://drive.google.com/uc?export=download&id=f1"

    async def test_duplicate_permission_is_swallowed(self, drive_service):
        drive_service.permissions.return_value.create.return_value.execute.side_effect = Exception(
            "Duplicate permission entry"
        )
        url = await resolve_public_media_url(None, make_row(media_url="/api/media/drive/file/f2"))
        assert url == "https://drive.google.com/uc?export=download&id=f2"

    async def test_other_permission_error_propagates(self, drive_service):
        drive_service.permissions.return_value.create.return_value.execute.side_effect = Exception(
            "insufficient authentication scopes"
        )
        with pytest.raises(Exception, match="insufficient authentication"):
            await resolve_public_media_url(None, make_row(media_url="/api/media/drive/file/f3"))


@pytest.mark.asyncio
class TestLocalOnlyMedia:
    async def test_relative_media_path_raises_not_public(self):
        row = make_row(media_url="/media/uploads/x.jpg")
        with pytest.raises(MediaNotPublicError, match="Google Drive"):
            await resolve_public_media_url(None, row)

    async def test_error_message_guides_the_user(self):
        with pytest.raises(MediaNotPublicError) as exc_info:
            await resolve_public_media_url(None, make_row(media_url="/media/x.jpg"))
        assert str(exc_info.value) == (
            "Media isn't publicly reachable — import it to Google Drive first, then reattach"
        )

    async def test_unparseable_catalog_ids_raises(self):
        row = make_row(media_catalog_ids="not-json")
        with pytest.raises(MediaNotPublicError):
            await resolve_public_media_url(None, row)

    async def test_dangling_catalog_id_raises(self, db_session):
        row = make_row(media_catalog_ids="[999]")
        with pytest.raises(MediaNotPublicError):
            await resolve_public_media_url(db_session, row)


@pytest.mark.asyncio
class TestCatalogMedia:
    async def seed_media(self, db_session, local_path, source="drive"):
        media = MediaCatalog(
            filename="a.jpg", local_path=local_path, mime_type="image/jpeg", source=source
        )
        db_session.add(media)
        await db_session.commit()
        return media

    async def test_drive_catalog_item_resolves(self, db_session, drive_service):
        media = await self.seed_media(db_session, "drive://fid42")
        row = make_row(media_catalog_ids=json.dumps([media.id]))
        url = await resolve_public_media_url(db_session, row)
        assert url == "https://drive.google.com/uc?export=download&id=fid42"
        assert permission_create_kwargs(drive_service)["fileId"] == "fid42"

    async def test_local_catalog_item_raises(self, db_session):
        media = await self.seed_media(db_session, "media/uploads/a.jpg", source="upload")
        row = make_row(media_catalog_ids=json.dumps([media.id]))
        with pytest.raises(MediaNotPublicError):
            await resolve_public_media_url(db_session, row)

    async def test_first_catalog_item_wins(self, db_session, drive_service):
        first = await self.seed_media(db_session, "drive://first-id")
        second = await self.seed_media(db_session, "drive://second-id")
        row = make_row(media_catalog_ids=json.dumps([first.id, second.id]))
        url = await resolve_public_media_url(db_session, row)
        assert url == "https://drive.google.com/uc?export=download&id=first-id"

    async def test_media_url_takes_precedence_over_catalog(self, db_session):
        media = await self.seed_media(db_session, "drive://fid")
        row = make_row(
            media_url="https://example.com/a.jpg",
            media_catalog_ids=json.dumps([media.id]),
        )
        assert await resolve_public_media_url(db_session, row) == "https://example.com/a.jpg"
