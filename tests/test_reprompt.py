"""Tests for re-prompting support (Task 9).

Covers:
- SheetsClient.get_rows_with_feedback()
- SheetsClient.clear_feedback()
- CaptionGenerator.generate_captions() with feedback parameter
- reprompt_pipeline() orchestration
"""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

from content_engine.models import ContentRow, ContentStatus, Platform


def _make_row(
    row_number: int = 2,
    status: ContentStatus = ContentStatus.PENDING_APPROVAL,
    feedback: str | None = "Make the caption more casual",
) -> ContentRow:
    """Build a ContentRow with feedback for testing."""
    return ContentRow(
        row_number=row_number,
        date=datetime(2026, 3, 1),
        content_pillar="Cow Life",
        raw_text="Baby Lakshmi playing in the meadow",
        platforms={
            Platform.INSTAGRAM: True,
            Platform.FACEBOOK: True,
            Platform.TIKTOK: False,
            Platform.THREADS: False,
            Platform.LINKEDIN: False,
        },
        status=status,
        captions={
            Platform.INSTAGRAM: "Old IG caption",
            Platform.FACEBOOK: "Old FB caption",
        },
        feedback=feedback,
    )


# ---------- SheetsClient.get_rows_with_feedback ----------


class TestGetRowsWithFeedback:
    """SheetsClient returns pending_approval rows that have feedback."""

    def test_returns_rows_with_feedback(self):
        from content_engine.sheets import SheetsClient

        with (
            patch("content_engine.sheets.build"),
            patch("content_engine.sheets.Credentials"),
        ):
            client = SheetsClient(
                credentials_path="/fake/creds.json",
                spreadsheet_id="fake-id",
            )

        # Build a pending_approval row with feedback in column S (index 18)
        row_data = [
            "2026-03-01",  # A: date
            "Cow Life",  # B: pillar
            "Baby calf born",  # C: raw_text
            "",  # D: media_url
            True,  # E: IG
            True,  # F: FB
            False,  # G: TT
            False,  # H: TH
            False,  # I: LI
            "pending_approval",  # J: status
            "Old IG caption",  # K: caption_ig
            "Old FB caption",  # L: caption_fb
            "",  # M: caption_tt
            "",  # N: caption_th
            "",  # O: caption_li
            "",  # P: postiz_ids
            "",  # Q: posted_at
            "",  # R: error_msg
            "Make it more casual",  # S: feedback
        ]

        mock_sheet = client.sheet
        mock_sheet.values().get().execute.return_value = {
            "values": [
                ["header"],  # header row
                row_data,
            ]
        }

        rows = client.get_rows_with_feedback()

        assert len(rows) == 1
        assert rows[0].feedback == "Make it more casual"
        assert rows[0].status == ContentStatus.PENDING_APPROVAL

    def test_excludes_rows_without_feedback(self):
        with (
            patch("content_engine.sheets.build"),
            patch("content_engine.sheets.Credentials"),
        ):
            from content_engine.sheets import SheetsClient

            client = SheetsClient(
                credentials_path="/fake/creds.json",
                spreadsheet_id="fake-id",
            )

        # Row with empty feedback
        row_no_feedback = [
            "2026-03-01",
            "Cow Life",
            "Baby calf",
            "",
            True,
            False,
            False,
            False,
            False,
            "pending_approval",
            "caption",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",  # S: empty feedback
        ]

        mock_sheet = client.sheet
        mock_sheet.values().get().execute.return_value = {"values": [["header"], row_no_feedback]}

        rows = client.get_rows_with_feedback()
        assert rows == []


# ---------- SheetsClient.clear_feedback ----------


class TestClearFeedback:
    """clear_feedback writes empty string to column S."""

    def test_clears_feedback_column(self):
        with (
            patch("content_engine.sheets.build"),
            patch("content_engine.sheets.Credentials"),
        ):
            from content_engine.sheets import SheetsClient

            client = SheetsClient(
                credentials_path="/fake/creds.json",
                spreadsheet_id="fake-id",
            )

        client.clear_feedback(row_number=5)

        mock_sheet = client.sheet
        mock_sheet.values().update.assert_called_once()
        call_str = str(mock_sheet.values().update.call_args)
        assert "S5" in call_str


# ---------- CaptionGenerator with feedback ----------


class TestGenerateCaptionsWithFeedback:
    """generate_captions appends feedback to the prompt when provided."""

    @patch("content_engine.generator.subprocess.run")
    def test_feedback_included_in_prompt(self, mock_run, tmp_path):
        from content_engine.generator import CaptionGenerator

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"instagram": "New IG caption", "facebook": "New FB caption"}),
            stderr="",
        )

        gen = CaptionGenerator(data_dir=tmp_path)
        row = _make_row()
        gen.generate_captions(row, feedback="Make it more casual and fun")

        # Check the prompt passed to Claude CLI
        call_args = mock_run.call_args
        prompt = call_args[0][0][2]  # ["claude", "-p", prompt]
        assert "Make it more casual and fun" in prompt
        assert "STAFF FEEDBACK" in prompt

    @patch("content_engine.generator.subprocess.run")
    def test_no_feedback_no_feedback_section(self, mock_run, tmp_path):
        from content_engine.generator import CaptionGenerator

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"instagram": "IG caption"}),
            stderr="",
        )

        gen = CaptionGenerator(data_dir=tmp_path)
        row = ContentRow(
            row_number=2,
            date=datetime(2026, 3, 1),
            content_pillar="Cow Life",
            raw_text="Baby calf born",
            platforms={Platform.INSTAGRAM: True},
            status=ContentStatus.READY,
            captions={},
        )
        gen.generate_captions(row)

        call_args = mock_run.call_args
        prompt = call_args[0][0][2]
        assert "STAFF FEEDBACK" not in prompt


# ---------- reprompt_pipeline ----------


class TestRepromptPipeline:
    """Test the reprompt pipeline orchestration."""

    def test_processes_feedback_rows(self):
        from content_engine.pipeline import reprompt_pipeline

        row = _make_row()
        sheets = MagicMock()
        sheets.get_rows_with_feedback.return_value = [row]

        postiz = MagicMock()
        postiz.list_integrations.return_value = [
            {"id": "int-ig", "platform": "instagram"},
            {"id": "int-fb", "platform": "facebook"},
        ]
        postiz.create_draft_post.return_value = {"id": "draft-new"}

        generator = MagicMock()
        generator.generate_captions.return_value = {
            Platform.INSTAGRAM: "New IG caption",
            Platform.FACEBOOK: "New FB caption",
        }

        result = reprompt_pipeline(
            sheets=sheets,
            postiz=postiz,
            generator=generator,
        )

        # Feedback passed to generator
        generator.generate_captions.assert_called_once_with(row, feedback=row.feedback)
        # Captions updated in sheet
        sheets.update_captions.assert_called_once()
        # Feedback cleared
        sheets.clear_feedback.assert_called_once_with(row.row_number)
        # Status reset to pending_approval
        sheets.update_status.assert_called_with(row.row_number, ContentStatus.PENDING_APPROVAL)
        assert result.processed == 1

    def test_no_feedback_rows(self):
        from content_engine.pipeline import reprompt_pipeline

        sheets = MagicMock()
        sheets.get_rows_with_feedback.return_value = []

        postiz = MagicMock()
        postiz.list_integrations.return_value = []

        generator = MagicMock()

        result = reprompt_pipeline(
            sheets=sheets,
            postiz=postiz,
            generator=generator,
        )

        assert result.processed == 0
        assert result.errors == 0
        generator.generate_captions.assert_not_called()

    def test_continues_after_row_failure(self):
        from content_engine.pipeline import reprompt_pipeline

        row1 = _make_row(row_number=2, feedback="Fix this")
        row2 = _make_row(row_number=3, feedback="Add hashtags")

        sheets = MagicMock()
        sheets.get_rows_with_feedback.return_value = [row1, row2]

        postiz = MagicMock()
        postiz.list_integrations.return_value = [
            {"id": "int-ig", "platform": "instagram"},
        ]
        postiz.create_draft_post.return_value = {"id": "draft-x"}

        generator = MagicMock()
        generator.generate_captions.side_effect = [
            RuntimeError("Claude CLI error"),
            {Platform.INSTAGRAM: "New IG"},
        ]

        result = reprompt_pipeline(
            sheets=sheets,
            postiz=postiz,
            generator=generator,
        )

        assert result.processed == 1
        assert result.errors == 1
        sheets.update_status.assert_any_call(
            row1.row_number, ContentStatus.ERROR, "Claude CLI error"
        )

    def test_creates_new_postiz_drafts(self):
        """Re-prompting creates fresh Postiz drafts for new captions."""
        from content_engine.pipeline import reprompt_pipeline

        row = _make_row()
        sheets = MagicMock()
        sheets.get_rows_with_feedback.return_value = [row]

        postiz = MagicMock()
        postiz.list_integrations.return_value = [
            {"id": "int-ig", "platform": "instagram"},
        ]
        postiz.create_draft_post.return_value = {"id": "draft-reprompt"}

        generator = MagicMock()
        generator.generate_captions.return_value = {
            Platform.INSTAGRAM: "Revised IG caption",
        }

        reprompt_pipeline(
            sheets=sheets,
            postiz=postiz,
            generator=generator,
        )

        postiz.create_draft_post.assert_called_once()
        sheets.update_postiz_ids.assert_called_once_with(row.row_number, "draft-reprompt")
