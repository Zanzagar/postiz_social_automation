"""Tests for Google Sheets sync adapter (Phase 1 — Task #3).

Tests cover:
- Migration: sheet_row_number and sheet_synced_at columns exist
- Import: READY rows from Sheet → SQLite with duplicate detection
- Export: status changes from SQLite → Sheet
- Background runner: error isolation
- Repository: find_by_sheet_row, get_rows_needing_sheet_sync, mark_sheet_synced
"""

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.models import Base
from api.repositories.content import ContentRepository
from content_engine.models import ContentPillar, ContentStatus, Platform
from content_engine.models import ContentRow as SheetContentRow


@pytest_asyncio.fixture
async def async_session():
    """Create an async in-memory SQLite session for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def repo(async_session):
    return ContentRepository(async_session)


def _make_sheet_row(
    row_number: int,
    raw_text: str = "Test content",
    status: ContentStatus = ContentStatus.READY,
    date: datetime | None = None,
    pillar: ContentPillar | None = ContentPillar.SPIRITUAL,
    platforms: dict | None = None,
    captions: dict | None = None,
) -> SheetContentRow:
    """Create a mock Sheet ContentRow (Pydantic model)."""
    return SheetContentRow(
        row_number=row_number,
        date=date or datetime(2026, 3, 17),
        content_pillar=pillar,
        raw_text=raw_text,
        platforms=platforms or {Platform.INSTAGRAM: True, Platform.FACEBOOK: True},
        status=status,
        captions=captions or {Platform.INSTAGRAM: "IG caption", Platform.FACEBOOK: "FB caption"},
    )


# --- Subtask 3.1: Migration columns ---


class TestSheetSyncColumns:
    """Verify the SQLAlchemy model has sheet sync columns."""

    @pytest.mark.asyncio
    async def test_content_row_has_sheet_row_number(self, repo, async_session):
        row = await repo.create_content_row({"raw_text": "Test", "sheet_row_number": 5})
        assert row.sheet_row_number == 5

    @pytest.mark.asyncio
    async def test_content_row_has_sheet_synced_at(self, repo, async_session):
        now = datetime.now(UTC)
        row = await repo.create_content_row({"raw_text": "Test", "sheet_synced_at": now})
        assert row.sheet_synced_at is not None

    @pytest.mark.asyncio
    async def test_sheet_row_number_defaults_to_none(self, repo, async_session):
        row = await repo.create_content_row({"raw_text": "No sheet"})
        assert row.sheet_row_number is None

    @pytest.mark.asyncio
    async def test_sheet_synced_at_defaults_to_none(self, repo, async_session):
        row = await repo.create_content_row({"raw_text": "No sheet"})
        assert row.sheet_synced_at is None


# --- Subtask 3.2: Repository - find_by_sheet_row ---


class TestRepoSheetMethods:
    @pytest.mark.asyncio
    async def test_find_by_sheet_row(self, repo, async_session):
        await repo.create_content_row(
            {"raw_text": "From sheet", "sheet_row_number": 7, "source": "sheet"}
        )
        found = await repo.find_by_sheet_row(7)
        assert found is not None
        assert found.raw_text == "From sheet"

    @pytest.mark.asyncio
    async def test_find_by_sheet_row_not_found(self, repo):
        found = await repo.find_by_sheet_row(999)
        assert found is None

    @pytest.mark.asyncio
    async def test_get_rows_needing_sheet_sync(self, repo, async_session):
        # Row from sheet with no sync timestamp = needs sync
        await repo.create_content_row(
            {
                "raw_text": "Needs sync",
                "source": "sheet",
                "sheet_row_number": 5,
                "status": "approved",
            }
        )
        # Row from manual = not from sheet, skip
        await repo.create_content_row({"raw_text": "Manual", "source": "manual", "status": "draft"})

        rows = await repo.get_rows_needing_sheet_sync()
        assert len(rows) == 1
        assert rows[0].raw_text == "Needs sync"

    @pytest.mark.asyncio
    async def test_get_rows_needing_sheet_sync_excludes_synced(self, repo, async_session):
        now = datetime.now(UTC)
        await repo.create_content_row(
            {
                "raw_text": "Already synced",
                "source": "sheet",
                "sheet_row_number": 5,
                "status": "approved",
                "sheet_synced_at": now,
                "updated_at": now,
            }
        )
        rows = await repo.get_rows_needing_sheet_sync()
        assert len(rows) == 0

    @pytest.mark.asyncio
    async def test_mark_sheet_synced(self, repo, async_session):
        row = await repo.create_content_row(
            {
                "raw_text": "To sync",
                "source": "sheet",
                "sheet_row_number": 10,
            }
        )
        await repo.mark_sheet_synced(row.id)

        updated = await repo.get_content_row(row.id)
        assert updated.sheet_synced_at is not None


# --- Subtask 3.2: import_ready_rows ---


class TestImportReadyRows:
    @pytest.fixture
    def mock_sheets(self):
        return MagicMock()

    @pytest.fixture
    def adapter(self, mock_sheets, repo):
        from api.adapters.sheets_sync import SheetsSyncAdapter

        return SheetsSyncAdapter(sheets_client=mock_sheets, repo=repo)

    @pytest.mark.asyncio
    async def test_import_single_ready_row(self, adapter, mock_sheets, repo):
        mock_sheets.get_rows_by_status.return_value = [
            _make_sheet_row(row_number=2, raw_text="Sunday Feast recap")
        ]

        imported_ids = await adapter.import_ready_rows()
        assert len(imported_ids) == 1

        # Verify it was stored in SQLite
        row = await repo.get_content_row(imported_ids[0])
        assert row.raw_text == "Sunday Feast recap"
        assert row.source == "sheet"
        assert row.sheet_row_number == 2
        assert row.status == "draft"

    @pytest.mark.asyncio
    async def test_import_skips_duplicate(self, adapter, mock_sheets, repo):
        # First import
        mock_sheets.get_rows_by_status.return_value = [
            _make_sheet_row(row_number=2, raw_text="Original")
        ]
        first_import = await adapter.import_ready_rows()
        assert len(first_import) == 1

        # Second import — same row_number, should be skipped
        mock_sheets.get_rows_by_status.return_value = [
            _make_sheet_row(row_number=2, raw_text="Original")
        ]
        second_import = await adapter.import_ready_rows()
        assert len(second_import) == 0

    @pytest.mark.asyncio
    async def test_import_marks_sheet_status(self, adapter, mock_sheets, repo):
        mock_sheets.get_rows_by_status.return_value = [_make_sheet_row(row_number=3)]
        await adapter.import_ready_rows()

        # Verify Sheet was updated to DRAFT
        mock_sheets.update_status.assert_called_once_with(3, ContentStatus.DRAFT)

    @pytest.mark.asyncio
    async def test_import_multiple_rows(self, adapter, mock_sheets, repo):
        mock_sheets.get_rows_by_status.return_value = [
            _make_sheet_row(row_number=2, raw_text="Row A"),
            _make_sheet_row(row_number=3, raw_text="Row B"),
            _make_sheet_row(row_number=4, raw_text="Row C"),
        ]
        imported = await adapter.import_ready_rows()
        assert len(imported) == 3

    @pytest.mark.asyncio
    async def test_import_stores_platforms_as_json(self, adapter, mock_sheets, repo):
        mock_sheets.get_rows_by_status.return_value = [
            _make_sheet_row(
                row_number=5,
                platforms={
                    Platform.INSTAGRAM: True,
                    Platform.FACEBOOK: False,
                    Platform.TIKTOK: True,
                },
            )
        ]
        imported = await adapter.import_ready_rows()
        row = await repo.get_content_row(imported[0])
        platforms = json.loads(row.platforms)
        assert platforms["instagram"] is True
        assert platforms["facebook"] is False

    @pytest.mark.asyncio
    async def test_import_stores_captions_as_json(self, adapter, mock_sheets, repo):
        mock_sheets.get_rows_by_status.return_value = [
            _make_sheet_row(
                row_number=6,
                captions={
                    Platform.INSTAGRAM: "IG text",
                    Platform.FACEBOOK: None,
                },
            )
        ]
        imported = await adapter.import_ready_rows()
        row = await repo.get_content_row(imported[0])
        captions = json.loads(row.captions)
        assert captions["instagram"] == "IG text"

    @pytest.mark.asyncio
    async def test_import_empty_sheet_returns_empty(self, adapter, mock_sheets):
        mock_sheets.get_rows_by_status.return_value = []
        imported = await adapter.import_ready_rows()
        assert imported == []


# --- Subtask 3.3: export_status_updates ---


class TestExportStatusUpdates:
    @pytest.fixture
    def mock_sheets(self):
        return MagicMock()

    @pytest.fixture
    def adapter(self, mock_sheets, repo):
        from api.adapters.sheets_sync import SheetsSyncAdapter

        return SheetsSyncAdapter(sheets_client=mock_sheets, repo=repo)

    @pytest.mark.asyncio
    async def test_export_updates_sheet_status(self, adapter, mock_sheets, repo):
        # Create a sheet-originated row that needs sync
        await repo.create_content_row(
            {
                "raw_text": "Approved content",
                "source": "sheet",
                "sheet_row_number": 5,
                "status": "approved",
            }
        )

        synced = await adapter.export_status_updates()
        assert synced == 1
        mock_sheets.update_status.assert_called_once_with(5, ContentStatus.APPROVED, None)

    @pytest.mark.asyncio
    async def test_export_with_postiz_ids(self, adapter, mock_sheets, repo):
        posted_at = datetime(2026, 3, 17, 12, 0, tzinfo=UTC)
        await repo.create_content_row(
            {
                "raw_text": "Posted content",
                "source": "sheet",
                "sheet_row_number": 8,
                "status": "posted",
                "postiz_ids": json.dumps(["pid-123", "pid-456"]),
                "posted_at": posted_at,
            }
        )

        synced = await adapter.export_status_updates()
        assert synced == 1
        mock_sheets.update_postiz_ids.assert_called_once()

    @pytest.mark.asyncio
    async def test_export_marks_as_synced(self, adapter, mock_sheets, repo):
        row = await repo.create_content_row(
            {
                "raw_text": "To export",
                "source": "sheet",
                "sheet_row_number": 10,
                "status": "approved",
            }
        )

        await adapter.export_status_updates()

        updated = await repo.get_content_row(row.id)
        assert updated.sheet_synced_at is not None

    @pytest.mark.asyncio
    async def test_export_skips_non_sheet_rows(self, adapter, mock_sheets, repo):
        await repo.create_content_row(
            {"raw_text": "Manual entry", "source": "manual", "status": "approved"}
        )

        synced = await adapter.export_status_updates()
        assert synced == 0
        mock_sheets.update_status.assert_not_called()

    @pytest.mark.asyncio
    async def test_export_with_error_msg(self, adapter, mock_sheets, repo):
        await repo.create_content_row(
            {
                "raw_text": "Failed content",
                "source": "sheet",
                "sheet_row_number": 12,
                "status": "error",
                "feedback": "API timeout",
            }
        )

        synced = await adapter.export_status_updates()
        assert synced == 1
        mock_sheets.update_status.assert_called_once_with(12, ContentStatus.ERROR, "API timeout")


# --- Subtask 3.4: Background runner ---


class TestSyncRunner:
    @pytest.mark.asyncio
    async def test_run_once_calls_import_and_export(self, repo):
        from api.adapters.sheets_sync import SheetsSyncAdapter

        mock_sheets = MagicMock()
        mock_sheets.get_rows_by_status.return_value = []
        adapter = SheetsSyncAdapter(sheets_client=mock_sheets, repo=repo)

        # run_sync_once is a single iteration (no loop)
        result = await adapter.run_sync_once()
        assert result is not None
        assert "imported" in result
        assert "exported" in result

    @pytest.mark.asyncio
    async def test_run_once_handles_import_error(self, repo):
        from api.adapters.sheets_sync import SheetsSyncAdapter

        mock_sheets = MagicMock()
        mock_sheets.get_rows_by_status.side_effect = Exception("Sheet API down")
        adapter = SheetsSyncAdapter(sheets_client=mock_sheets, repo=repo)

        # Should not raise — error is caught and returned
        result = await adapter.run_sync_once()
        assert result["error"] is not None
