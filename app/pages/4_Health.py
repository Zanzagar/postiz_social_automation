"""System Health page — check connectivity to all external services."""

import os

import streamlit as st

from content_engine.health import (
    check_claude_health,
    check_oauth_health,
    check_postiz_health,
    check_sheets_health,
)

st.set_page_config(page_title="System Health", page_icon="\U0001f3e5", layout="wide")

from app.auth import check_password  # noqa: E402

if not check_password():
    st.stop()

st.title("System Health")
st.markdown("Check connectivity to Google Sheets, Postiz API, and Claude CLI.")

# Build clients from env vars if available
sheets_client = None
postiz_client = None

if os.getenv("GOOGLE_SHEETS_CREDENTIALS") and os.getenv("SPREADSHEET_ID"):
    try:
        from content_engine.sheets import SheetsClient

        sheets_client = SheetsClient(
            credentials_path=os.environ["GOOGLE_SHEETS_CREDENTIALS"],
            spreadsheet_id=os.environ["SPREADSHEET_ID"],
        )
    except Exception:
        st.error("Failed to initialize Sheets client. Check credentials.")

if os.getenv("POSTIZ_API_KEY"):
    try:
        from content_engine.postiz import PostizClient

        postiz_client = PostizClient(
            api_key=os.environ["POSTIZ_API_KEY"],
            base_url=os.getenv("POSTIZ_BASE_URL", "https://postiz.sethpc.xyz/api/public/v1"),
        )
    except Exception:
        st.error("Failed to initialize Postiz client. Check API key.")

# Run health checks
col1, col2, col3, col4 = st.columns(4)

sheets_ok, sheets_msg = check_sheets_health(sheets_client=sheets_client, skip_if_none=True)
postiz_ok, postiz_msg = check_postiz_health(postiz_client=postiz_client)
claude_ok, claude_msg = check_claude_health()
oauth_ok, oauth_msg = check_oauth_health()

with col1:
    status = "OK" if sheets_ok else "Error"
    st.metric("Google Sheets", status)
    if sheets_ok:
        st.success(sheets_msg)
    else:
        st.error(sheets_msg)

with col2:
    status = "OK" if postiz_ok else "Error"
    st.metric("Postiz API", status)
    if postiz_ok:
        st.success(postiz_msg)
    else:
        st.error(postiz_msg)

with col3:
    status = "OK" if claude_ok else "Error"
    st.metric("Claude CLI", status)
    if claude_ok:
        st.success(claude_msg)
    else:
        st.error(claude_msg)

with col4:
    status = "OK" if oauth_ok else "Error"
    st.metric("OAuth Token", status)
    if oauth_ok:
        st.success(oauth_msg)
    else:
        st.error(oauth_msg)

# Recent errors section
st.divider()
st.subheader("Recent Errors")

if sheets_client:
    try:
        errors = sheets_client.get_recent_errors(limit=10)
        if errors:
            for err in reversed(errors):
                row_info = f" (row {err['row']})" if err["row"] else ""
                st.error(f"**{err['timestamp']}** [{err['source']}]{row_info}: {err['message']}")
        else:
            st.success("No recent errors.")
    except Exception:
        st.warning("Could not fetch error logs.")
else:
    st.info("Configure Google Sheets credentials to view error logs.")
