"""Suggestions page — browse and accept AI-generated content ideas."""

import os

import streamlit as st

from content_engine.models import ContentPillar

st.set_page_config(page_title="Suggestions", page_icon="\U0001f4a1", layout="wide")

st.title("Content Suggestions")
st.markdown("Browse AI-generated content ideas based on calendar gaps and pillar balance.")

# ---------------------------------------------------------------------------
# Initialize Sheets client
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Filter controls
# ---------------------------------------------------------------------------

col1, col2 = st.columns([1, 1])
with col1:
    pillar_options = ["All"] + [p.value for p in ContentPillar]
    pillar_filter = st.selectbox("Filter by pillar", pillar_options)
with col2:
    status_filter = st.selectbox("Status", ["suggested", "accepted", "dismissed"])

# ---------------------------------------------------------------------------
# Load and display suggestions
# ---------------------------------------------------------------------------

if st.session_state.sheets_client:
    try:
        from app.pages.suggestions_helpers import filter_suggestions, prepare_accept_data

        all_suggestions = st.session_state.sheets_client.get_suggestions()
        suggestions = filter_suggestions(
            all_suggestions, pillar_filter=pillar_filter, status_filter=status_filter
        )

        if not suggestions:
            st.info("No suggestions found. Run the suggest pipeline to generate new ideas.")
        else:
            for i, suggestion in enumerate(suggestions):
                with st.container():
                    st.markdown(f"### {suggestion.suggested_pillar.value}")
                    st.write(suggestion.content_idea)
                    st.caption(f"Suggested for: {suggestion.suggested_date.strftime('%Y-%m-%d')}")
                    st.caption(f"Rationale: {suggestion.rationale}")
                    st.caption(f"Media suggestion: {suggestion.media_suggestion}")

                    btn_col1, btn_col2, _ = st.columns([1, 1, 3])
                    with btn_col1:
                        if st.button("Accept", key=f"accept_{i}"):
                            data = prepare_accept_data(suggestion)
                            for key, val in data.items():
                                st.session_state[key] = val
                            st.switch_page("pages/1_Create_Review.py")
                    with btn_col2:
                        if st.button("Dismiss", key=f"dismiss_{i}"):
                            st.info("Dismiss functionality requires update_suggestion_status.")

                    st.divider()

    except Exception as e:
        st.error(f"Failed to load suggestions: {e}")
else:
    st.info("Configure Google Sheets credentials to view suggestions.")
