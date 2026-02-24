"""Calendar page — view scheduled and planned content."""

import json
import os
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Content Calendar", page_icon="\U0001f4c5", layout="wide")

from app.auth import check_password  # noqa: E402

if not check_password():
    st.stop()

st.title("Content Calendar")
st.markdown("View and manage your content schedule across all platforms.")

# ---------------------------------------------------------------------------
# Load scheduled content from Google Sheets or local data
# ---------------------------------------------------------------------------

rows = []

if "sheets_client" not in st.session_state:
    creds = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
    sheet_id = os.getenv("SPREADSHEET_ID")
    if creds and sheet_id:
        try:
            from content_engine.sheets import SheetsClient

            st.session_state.sheets_client = SheetsClient(
                credentials_path=creds,
                spreadsheet_id=sheet_id,
            )
        except Exception as e:
            st.error(f"Failed to initialize Sheets client: {e}")
            st.session_state.sheets_client = None
    else:
        st.session_state.sheets_client = None

if st.session_state.get("sheets_client"):
    try:
        from content_engine.models import ContentStatus

        for status in [ContentStatus.APPROVED, ContentStatus.SCHEDULED, ContentStatus.PUBLISHED]:
            rows.extend(st.session_state.sheets_client.get_rows_by_status(status))
    except Exception as e:
        st.error(f"Failed to load content: {e}")

# ---------------------------------------------------------------------------
# Display calendar view
# ---------------------------------------------------------------------------

if rows:
    # Group by date
    by_date: dict[str, list] = {}
    for row in rows:
        date_key = row.date.strftime("%Y-%m-%d") if row.date else "Unscheduled"
        by_date.setdefault(date_key, []).append(row)

    for date_key in sorted(by_date.keys()):
        st.subheader(date_key)
        for row in by_date[date_key]:
            platforms = [p.value for p, enabled in row.platforms.items() if enabled]
            status_emoji = {
                "approved": "\u2705",
                "scheduled": "\U0001f4c5",
                "published": "\U0001f680",
            }.get(row.status.value if hasattr(row.status, "value") else str(row.status), "\u2753")

            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.write(f"{status_emoji} {row.raw_text[:80]}...")
            with col2:
                st.caption(", ".join(platforms) if platforms else "No platforms")
            with col3:
                st.caption(row.status.value if hasattr(row.status, "value") else str(row.status))
        st.divider()
else:
    # Check for local suggestion data as fallback
    suggestions_path = Path("data") / "suggestions.json"
    if suggestions_path.exists():
        try:
            suggestions = json.loads(suggestions_path.read_text())
            st.info(
                f"{len(suggestions)} content suggestions available. "
                "Accept them on the Suggestions page to populate the calendar."
            )
        except Exception:
            pass

    if not rows:
        st.info(
            "No scheduled content yet. Content appears here after being approved on the "
            "Create & Review or Drafts page.\n\n"
            "**To get started:**\n"
            "1. Configure Google Sheets credentials in `.env`\n"
            "2. Create content on the **Create & Review** page\n"
            "3. Approved content will appear here organized by date"
        )
