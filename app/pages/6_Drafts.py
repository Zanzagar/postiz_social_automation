"""Drafts Review page — review pending drafts, edit captions, batch approve."""

import os

import streamlit as st

from app.helpers.drafts_helpers import (
    apply_caption_edits,
    build_postiz_link,
    get_caption_for_platform,
    get_enabled_platforms,
)
from content_engine.models import ContentStatus

st.set_page_config(page_title="Review Drafts", page_icon="\U0001f4cb", layout="wide")

from app.auth import check_password  # noqa: E402

if not check_password():
    st.stop()

st.title("Review Drafts")
st.markdown("Review pending drafts, edit captions inline, and batch-approve to Postiz.")

# ---------------------------------------------------------------------------
# Initialize clients
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

if "postiz_client" not in st.session_state:
    api_key = os.getenv("POSTIZ_API_KEY")
    if api_key:
        from content_engine.postiz import PostizClient

        st.session_state.postiz_client = PostizClient(
            api_key=api_key,
            base_url=os.getenv("POSTIZ_BASE_URL", "https://postiz.sethpc.xyz/api/public/v1"),
        )
    else:
        st.session_state.postiz_client = None

# ---------------------------------------------------------------------------
# Load pending drafts
# ---------------------------------------------------------------------------

if not st.session_state.sheets_client:
    st.info("Configure Google Sheets credentials to view drafts.")
    st.stop()

try:
    drafts = st.session_state.sheets_client.get_rows_by_status(ContentStatus.PENDING_APPROVAL)
except Exception as e:
    st.error(f"Failed to load drafts: {e}")
    st.stop()

if not drafts:
    st.success("No pending drafts. All caught up!")
    st.stop()

st.info(f"{len(drafts)} draft(s) pending review")

# ---------------------------------------------------------------------------
# Batch selection + draft cards
# ---------------------------------------------------------------------------

select_all = st.checkbox("Select all")

selected_rows: list[int] = []

for draft in drafts:
    with st.container():
        col1, col2 = st.columns([3, 1])

        with col1:
            is_selected = st.checkbox(
                f"Row {draft.row_number}: {draft.raw_text[:60]}",
                value=select_all,
                key=f"select_{draft.row_number}",
            )
            if is_selected:
                selected_rows.append(draft.row_number)

            # Platform caption tabs
            enabled = get_enabled_platforms(draft)
            if enabled:
                tabs = st.tabs([p.value.title() for p in enabled])
                for tab, platform in zip(tabs, enabled):
                    with tab:
                        current = get_caption_for_platform(draft, platform)
                        edited = st.text_area(
                            f"Edit {platform.value}",
                            value=current,
                            key=f"edit_{draft.row_number}_{platform.value}",
                            height=120,
                        )
                        # Track edits in session state
                        if edited != current:
                            edit_key = f"draft_edits_{draft.row_number}"
                            if edit_key not in st.session_state:
                                st.session_state[edit_key] = {}
                            st.session_state[edit_key][platform] = edited

        with col2:
            # Re-prompt
            feedback = st.text_input(
                "Re-prompt",
                key=f"reprompt_{draft.row_number}",
                placeholder="Make it shorter...",
            )
            if st.button("Regenerate", key=f"regen_{draft.row_number}"):
                if feedback and st.session_state.get("generator"):
                    from app.helpers.create_post_helpers import regenerate_with_feedback

                    with st.spinner("Regenerating..."):
                        try:
                            updated = regenerate_with_feedback(
                                generator=st.session_state.generator,
                                row=draft,
                                feedback=feedback,
                            )
                            # Write updated captions back to sheet
                            st.session_state.sheets_client.update_captions(
                                draft.row_number, updated
                            )
                            st.rerun()
                        except Exception as e:
                            st.error(f"Regeneration failed: {e}")
                else:
                    st.warning("Enter feedback and ensure AI generator is available.")

            # Postiz link
            link = build_postiz_link(draft.postiz_ids)
            if link:
                st.markdown(f"[Open in Postiz]({link})")

        st.divider()

# ---------------------------------------------------------------------------
# Batch approve
# ---------------------------------------------------------------------------

selected_drafts = [d for d in drafts if d.row_number in selected_rows]

if selected_drafts:
    if st.button(f"Approve & Send {len(selected_drafts)} to Postiz", type="primary"):
        if not st.session_state.postiz_client:
            st.error("Set POSTIZ_API_KEY to enable sending to Postiz.")
        else:
            from app.helpers.create_post_helpers import send_to_postiz

            with st.spinner("Approving and creating Postiz drafts..."):
                success_count = 0
                for draft in selected_drafts:
                    try:
                        # Apply any pending edits
                        edit_key = f"draft_edits_{draft.row_number}"
                        if edit_key in st.session_state:
                            draft = apply_caption_edits(draft, st.session_state[edit_key])
                            st.session_state.sheets_client.update_captions(
                                draft.row_number,
                                {p: c for p, c in draft.captions.items() if c},
                            )

                        # Update status to approved
                        st.session_state.sheets_client.update_status(
                            draft.row_number, ContentStatus.APPROVED
                        )

                        # Send to Postiz
                        active_captions = {
                            p: c for p, c in draft.captions.items() if c and draft.platforms.get(p)
                        }
                        if active_captions:
                            draft_ids = send_to_postiz(
                                postiz=st.session_state.postiz_client,
                                captions=active_captions,
                                media_url=str(draft.media_url) if draft.media_url else None,
                                scheduled_at=None,
                            )
                            if draft_ids:
                                st.session_state.sheets_client.update_postiz_ids(
                                    draft.row_number, ",".join(draft_ids)
                                )
                        success_count += 1
                    except Exception as e:
                        st.error(f"Failed to approve row {draft.row_number}: {e}")

                if success_count:
                    st.success(f"{success_count} draft(s) approved and sent to Postiz!")
                    st.rerun()
