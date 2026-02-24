"""Tests for Google Sheets integration with mocked API responses."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from content_engine.models import ContentPillar, ContentRow, ContentStatus, Platform, Suggestion
from content_engine.sheets import SheetsClient

# Column layout: A=date, B=pillar, C=raw_text, D=media_url,
# E-I=platform checkboxes (IG,FB,TT,TH,LI), J=status,
# K-O=captions (IG,FB,TT,TH,LI), P=postiz_ids, Q=posted_at, R=error_msg

SAMPLE_ROW = [
    "2026-03-01",  # A: date
    "Cow Life",  # B: pillar
    "Baby calf born this morning!",  # C: raw_text
    "https://drive.google.com/file/d/abc123",  # D: media_url
    True,  # E: IG
    True,  # F: FB
    False,  # G: TT
    False,  # H: TH
    False,  # I: LI
    "ready",  # J: status
    "",  # K: caption_ig
    "",  # L: caption_fb
    "",  # M: caption_tt
    "",  # N: caption_th
    "",  # O: caption_li
    "",  # P: postiz_ids
    "",  # Q: posted_at
    "",  # R: error_msg
]


@pytest.fixture
def mock_service():
    """Create a mock Google Sheets service."""
    service = MagicMock()
    return service


@pytest.fixture
def client(mock_service):
    """Create a SheetsClient with mocked service."""
    with (
        patch("content_engine.sheets.build") as mock_build,
        patch("content_engine.sheets.Credentials"),
    ):
        mock_build.return_value = mock_service
        c = SheetsClient(
            credentials_path="/fake/creds.json",
            spreadsheet_id="fake-spreadsheet-id",
        )
    # Replace the service with our mock for direct control
    c.service = mock_service
    c.sheet = mock_service.spreadsheets()
    return c


class TestGetRowsByStatus:
    def test_returns_content_rows_for_ready_status(self, client, mock_service) -> None:
        """get_rows_by_status('ready') returns ContentRow objects."""
        mock_service.spreadsheets().values().get().execute.return_value = {
            "values": [
                # Header row (skipped)
                [
                    "date",
                    "content_pillar",
                    "raw_text",
                    "media_url",
                    "IG",
                    "FB",
                    "TT",
                    "TH",
                    "LI",
                    "status",
                ],
                SAMPLE_ROW,
            ]
        }

        rows = client.get_rows_by_status(ContentStatus.READY)

        assert len(rows) == 1
        assert isinstance(rows[0], ContentRow)
        assert rows[0].raw_text == "Baby calf born this morning!"
        assert rows[0].status == ContentStatus.READY
        assert rows[0].row_number == 2
        assert rows[0].platforms[Platform.INSTAGRAM] is True
        assert rows[0].platforms[Platform.FACEBOOK] is True
        assert rows[0].platforms.get(Platform.TIKTOK) is False

    def test_filters_by_status(self, client, mock_service) -> None:
        """Only rows matching the requested status are returned."""
        draft_row = list(SAMPLE_ROW)
        draft_row[9] = "draft"  # J: status

        mock_service.spreadsheets().values().get().execute.return_value = {
            "values": [
                ["date", "content_pillar"],  # header
                SAMPLE_ROW,  # ready
                draft_row,  # draft
            ]
        }

        rows = client.get_rows_by_status(ContentStatus.READY)
        assert len(rows) == 1
        assert rows[0].status == ContentStatus.READY

    def test_empty_sheet_returns_empty_list(self, client, mock_service) -> None:
        mock_service.spreadsheets().values().get().execute.return_value = {
            "values": [["date", "content_pillar"]]  # header only
        }

        rows = client.get_rows_by_status(ContentStatus.READY)
        assert rows == []


class TestUpdateCaptions:
    def test_writes_captions_to_correct_range(self, client, mock_service) -> None:
        """Captions written to K-O for the given row number."""
        captions = {
            Platform.INSTAGRAM: "IG caption here",
            Platform.FACEBOOK: "FB caption here",
        }

        client.update_captions(row_number=2, captions=captions)

        mock_service.spreadsheets().values().update.assert_called_once()
        call_kwargs = mock_service.spreadsheets().values().update.call_args
        assert "K2:O2" in str(call_kwargs)


class TestUpdateStatus:
    def test_updates_status_column(self, client, mock_service) -> None:
        client.update_status(row_number=3, status=ContentStatus.PENDING_APPROVAL)

        mock_service.spreadsheets().values().update.assert_called_once()
        call_kwargs = mock_service.spreadsheets().values().update.call_args
        assert "J3" in str(call_kwargs)

    def test_updates_status_with_error_msg(self, client, mock_service) -> None:
        client.update_status(
            row_number=3,
            status=ContentStatus.ERROR,
            error_msg="API rate limit exceeded",
        )

        # Should update both J (status) and R (error_msg)
        assert mock_service.spreadsheets().values().update.call_count >= 1


class TestUpdatePostizIds:
    def test_writes_postiz_ids_and_timestamp(self, client, mock_service) -> None:
        posted_at = datetime(2026, 3, 1, 14, 30)
        client.update_postiz_ids(
            row_number=2,
            postiz_ids="post_123,post_456",
            posted_at=posted_at,
        )

        mock_service.spreadsheets().values().update.assert_called()
        call_args_str = str(mock_service.spreadsheets().values().update.call_args_list)
        assert "P2" in call_args_str


class TestSuggestions:
    def test_add_suggestion_appends_row(self, client, mock_service) -> None:
        suggestion = Suggestion(
            suggested_date=datetime(2026, 3, 15),
            content_idea="Spring planting photo series",
            suggested_pillar=ContentPillar.FARM_OPS,
            rationale="Spring content performs well",
            media_suggestion="Photos of seedlings",
        )

        client.add_suggestion(suggestion)

        mock_service.spreadsheets().values().append.assert_called_once()

    def test_get_suggestions_returns_list(self, client, mock_service) -> None:
        mock_service.spreadsheets().values().get().execute.return_value = {
            "values": [
                ["date", "idea", "pillar", "rationale", "media", "status"],  # header
                [
                    "2026-03-15",
                    "Spring planting",
                    "Farm Ops",
                    "Good season",
                    "Photos",
                    "suggested",
                ],
            ]
        }

        suggestions = client.get_suggestions()
        assert len(suggestions) == 1
        assert isinstance(suggestions[0], Suggestion)


class TestRetryLogic:
    def test_retries_on_api_error(self, client, mock_service) -> None:
        """API errors trigger retry with backoff."""
        from googleapiclient.errors import HttpError

        mock_resp = MagicMock()
        mock_resp.status = 429
        mock_resp.reason = "Rate Limit Exceeded"

        error = HttpError(resp=mock_resp, content=b"rate limit")

        # First two calls fail, third succeeds
        mock_service.spreadsheets().values().get().execute.side_effect = [
            error,
            error,
            {"values": [["header"], SAMPLE_ROW]},
        ]

        with patch("content_engine.sheets.time.sleep"):
            rows = client.get_rows_by_status(ContentStatus.READY)

        assert len(rows) == 1
