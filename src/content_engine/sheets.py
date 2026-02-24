"""Google Sheets integration for content intake.

Column layout (Content Calendar tab):
  A=date, B=pillar, C=raw_text, D=media_url,
  E-I=platform checkboxes (IG,FB,TT,TH,LI), J=status,
  K-O=captions (IG,FB,TT,TH,LI), P=postiz_ids, Q=posted_at, R=error_msg,
  S=feedback

Column layout (Suggestions tab):
  A=date, B=idea, C=pillar, D=rationale, E=media_suggestion, F=status
"""

import logging
import time
from datetime import datetime

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from content_engine.models import ContentPillar, ContentRow, ContentStatus, Platform, Suggestion

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Platform column indices (0-based within the row)
_PLATFORM_COLS = [
    (4, Platform.INSTAGRAM),
    (5, Platform.FACEBOOK),
    (6, Platform.TIKTOK),
    (7, Platform.THREADS),
    (8, Platform.LINKEDIN),
]

# Caption column indices
_CAPTION_PLATFORMS = [
    Platform.INSTAGRAM,
    Platform.FACEBOOK,
    Platform.TIKTOK,
    Platform.THREADS,
    Platform.LINKEDIN,
]

MAX_RETRIES = 3
BACKOFF_BASE = 1.0  # seconds


def _retry(func):
    """Decorator for exponential backoff retry on HttpError."""

    def wrapper(*args, **kwargs):
        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except HttpError as e:
                if attempt == MAX_RETRIES - 1:
                    raise
                wait = BACKOFF_BASE * (2**attempt)
                logger.warning(
                    "API error (attempt %d/%d): %s. Retrying in %.1fs",
                    attempt + 1,
                    MAX_RETRIES,
                    e,
                    wait,
                )
                time.sleep(wait)

    return wrapper


def _safe_get(row: list, index: int, default: str = "") -> str:
    """Get value from row list, returning default if index is out of range."""
    if index < len(row):
        val = row[index]
        if val is None:
            return default
        return str(val)
    return default


def _parse_bool(val) -> bool:
    """Parse a checkbox value from Sheets (TRUE/FALSE/True/False/bool)."""
    if isinstance(val, bool):
        return val
    return str(val).upper() == "TRUE"


def _parse_content_row(row: list, row_number: int) -> ContentRow | None:
    """Parse a raw Sheets row into a ContentRow model. Returns None on parse error."""
    try:
        date_str = _safe_get(row, 0)
        if not date_str:
            return None

        pillar_str = _safe_get(row, 1)
        content_pillar = None
        if pillar_str:
            try:
                content_pillar = ContentPillar(pillar_str)
            except ValueError:
                logger.warning("Unknown pillar '%s' in row %d", pillar_str, row_number)

        raw_text = _safe_get(row, 2)
        media_url = _safe_get(row, 3) or None

        platforms = {}
        for col_idx, platform in _PLATFORM_COLS:
            platforms[platform] = _parse_bool(row[col_idx]) if col_idx < len(row) else False

        status_str = _safe_get(row, 9)
        status = ContentStatus(status_str) if status_str else ContentStatus.DRAFT

        captions: dict[Platform, str | None] = {}
        for i, platform in enumerate(_CAPTION_PLATFORMS):
            cap = _safe_get(row, 10 + i)
            captions[platform] = cap if cap else None

        postiz_ids = _safe_get(row, 15) or None
        posted_at_str = _safe_get(row, 16)
        posted_at = datetime.fromisoformat(posted_at_str) if posted_at_str else None
        error_msg = _safe_get(row, 17) or None
        feedback = _safe_get(row, 18) or None

        return ContentRow(
            row_number=row_number,
            date=datetime.fromisoformat(date_str),
            content_pillar=content_pillar,
            raw_text=raw_text,
            media_url=media_url,
            platforms=platforms,
            status=status,
            captions=captions,
            postiz_ids=postiz_ids,
            posted_at=posted_at,
            error_msg=error_msg,
            feedback=feedback,
        )
    except Exception:
        logger.exception("Failed to parse row %d", row_number)
        return None


class SheetsClient:
    """Client for Google Sheets Content Calendar operations."""

    def __init__(self, credentials_path: str, spreadsheet_id: str) -> None:
        self.spreadsheet_id = spreadsheet_id
        creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
        self.service = build("sheets", "v4", credentials=creds)
        self.sheet = self.service.spreadsheets()

    @_retry
    def get_rows_by_status(
        self, status: ContentStatus, tab: str = "Content Calendar"
    ) -> list[ContentRow]:
        """Fetch all rows with the given status."""
        result = (
            self.sheet.values()
            .get(spreadsheetId=self.spreadsheet_id, range=f"'{tab}'!A:S")
            .execute()
        )
        all_rows = result.get("values", [])
        if len(all_rows) <= 1:
            return []  # header only or empty

        rows = []
        for i, row in enumerate(all_rows[1:], start=2):  # row_number is 1-indexed, skip header
            status_val = _safe_get(row, 9)
            if status_val == status.value:
                parsed = _parse_content_row(row, row_number=i)
                if parsed:
                    rows.append(parsed)
        return rows

    @_retry
    def get_all_content_rows(self, tab: str = "Content Calendar") -> list[ContentRow]:
        """Fetch all content rows regardless of status."""
        result = (
            self.sheet.values()
            .get(spreadsheetId=self.spreadsheet_id, range=f"'{tab}'!A:S")
            .execute()
        )
        all_rows = result.get("values", [])
        if len(all_rows) <= 1:
            return []

        rows = []
        for i, row in enumerate(all_rows[1:], start=2):
            parsed = _parse_content_row(row, row_number=i)
            if parsed:
                rows.append(parsed)
        return rows

    @_retry
    def update_captions(self, row_number: int, captions: dict[Platform, str]) -> None:
        """Write AI-generated captions to columns K-O for the given row."""
        values = []
        for platform in _CAPTION_PLATFORMS:
            values.append(captions.get(platform, ""))

        (
            self.sheet.values()
            .update(
                spreadsheetId=self.spreadsheet_id,
                range=f"'Content Calendar'!K{row_number}:O{row_number}",
                valueInputOption="RAW",
                body={"values": [values]},
            )
            .execute()
        )

    @_retry
    def update_status(
        self,
        row_number: int,
        status: ContentStatus,
        error_msg: str | None = None,
    ) -> None:
        """Update the status column (J) and optionally error_msg (R)."""
        (
            self.sheet.values()
            .update(
                spreadsheetId=self.spreadsheet_id,
                range=f"'Content Calendar'!J{row_number}",
                valueInputOption="RAW",
                body={"values": [[status.value]]},
            )
            .execute()
        )

        if error_msg is not None:
            (
                self.sheet.values()
                .update(
                    spreadsheetId=self.spreadsheet_id,
                    range=f"'Content Calendar'!R{row_number}",
                    valueInputOption="RAW",
                    body={"values": [[error_msg]]},
                )
                .execute()
            )

    @_retry
    def update_postiz_ids(
        self,
        row_number: int,
        postiz_ids: str,
        posted_at: datetime | None = None,
    ) -> None:
        """Write Postiz post IDs (P) and posted timestamp (Q)."""
        values = [postiz_ids, posted_at.isoformat() if posted_at else ""]
        (
            self.sheet.values()
            .update(
                spreadsheetId=self.spreadsheet_id,
                range=f"'Content Calendar'!P{row_number}:Q{row_number}",
                valueInputOption="RAW",
                body={"values": [values]},
            )
            .execute()
        )

    @_retry
    def get_rows_with_feedback(self, tab: str = "Content Calendar") -> list[ContentRow]:
        """Fetch rows with status='pending_approval' and non-empty feedback (col S)."""
        result = (
            self.sheet.values()
            .get(spreadsheetId=self.spreadsheet_id, range=f"'{tab}'!A:S")
            .execute()
        )
        all_rows = result.get("values", [])
        if len(all_rows) <= 1:
            return []

        rows = []
        for i, row in enumerate(all_rows[1:], start=2):
            status_val = _safe_get(row, 9)
            feedback_val = _safe_get(row, 18)
            if status_val == ContentStatus.PENDING_APPROVAL.value and feedback_val:
                parsed = _parse_content_row(row, row_number=i)
                if parsed:
                    rows.append(parsed)
        return rows

    @_retry
    def clear_feedback(self, row_number: int) -> None:
        """Clear the feedback column (S) for the given row."""
        (
            self.sheet.values()
            .update(
                spreadsheetId=self.spreadsheet_id,
                range=f"'Content Calendar'!S{row_number}",
                valueInputOption="RAW",
                body={"values": [[""]]},
            )
            .execute()
        )

    @_retry
    def add_suggestion(self, suggestion: Suggestion, tab: str = "Suggestions") -> None:
        """Append a new suggestion to the Suggestions tab."""
        values = [
            suggestion.suggested_date.isoformat(),
            suggestion.content_idea,
            suggestion.suggested_pillar.value,
            suggestion.rationale,
            suggestion.media_suggestion,
            suggestion.status,
        ]
        (
            self.sheet.values()
            .append(
                spreadsheetId=self.spreadsheet_id,
                range=f"'{tab}'!A:F",
                valueInputOption="RAW",
                body={"values": [values]},
            )
            .execute()
        )

    @_retry
    def get_suggestions(
        self, status: str | None = None, tab: str = "Suggestions"
    ) -> list[Suggestion]:
        """Read suggestions, optionally filtered by status."""
        result = (
            self.sheet.values()
            .get(spreadsheetId=self.spreadsheet_id, range=f"'{tab}'!A:F")
            .execute()
        )
        all_rows = result.get("values", [])
        if len(all_rows) <= 1:
            return []

        suggestions = []
        for row in all_rows[1:]:
            row_status = _safe_get(row, 5, "suggested")
            if status and row_status != status:
                continue
            try:
                suggestions.append(
                    Suggestion(
                        suggested_date=datetime.fromisoformat(_safe_get(row, 0)),
                        content_idea=_safe_get(row, 1),
                        suggested_pillar=ContentPillar(_safe_get(row, 2)),
                        rationale=_safe_get(row, 3),
                        media_suggestion=_safe_get(row, 4),
                        status=row_status,
                    )
                )
            except Exception:
                logger.exception("Failed to parse suggestion row")
        return suggestions
