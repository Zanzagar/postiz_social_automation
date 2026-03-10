"""Create & Review page — generate AI captions and send to Postiz."""

import os
from datetime import datetime

import streamlit as st

from content_engine.models import Platform

st.set_page_config(page_title="Create & Review", page_icon="\u270d\ufe0f", layout="wide")

from app.auth import check_password  # noqa: E402

if not check_password():
    st.stop()

st.title("Create & Review")
st.markdown("Generate AI captions from raw content and review before scheduling.")

# ---------------------------------------------------------------------------
# Initialize clients in session state
# ---------------------------------------------------------------------------

if "generator" not in st.session_state:
    try:
        from content_engine.generator import CaptionGenerator

        st.session_state.generator = CaptionGenerator()
    except Exception as e:
        st.error(f"Failed to initialize AI generator: {e}")
        st.session_state.generator = None

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
# Input form
# ---------------------------------------------------------------------------

with st.form("create_post_form"):
    col1, col2 = st.columns([2, 1])

    with col1:
        caption = st.text_area(
            "Your caption (1 sentence is enough!)",
            placeholder="Lakshmi enjoying the morning sun...",
            height=120,
        )
        media_url = st.text_input(
            "Google Drive media URL (optional)",
            placeholder="https://drive.google.com/file/d/.../view",
        )

    with col2:
        st.subheader("Platforms")
        ig = st.checkbox("Instagram", value=True)
        fb = st.checkbox("Facebook", value=True)
        tt = st.checkbox("TikTok", value=True)
        th = st.checkbox("Threads", value=True)
        li = st.checkbox("LinkedIn", value=False)

    scheduled_date = st.date_input("Scheduled date", value=datetime.now())

    generate_btn = st.form_submit_button("Generate for All Platforms", type="primary")

# ---------------------------------------------------------------------------
# Generate captions
# ---------------------------------------------------------------------------

if generate_btn:
    if not caption:
        st.warning("Please enter a caption before generating.")
    elif not st.session_state.generator:
        st.error("AI generator not available. Check Claude CLI configuration.")
    else:
        from app.helpers.create_post_helpers import build_content_row, generate_captions

        platforms = {}
        if ig:
            platforms[Platform.INSTAGRAM] = True
        if fb:
            platforms[Platform.FACEBOOK] = True
        if tt:
            platforms[Platform.TIKTOK] = True
        if th:
            platforms[Platform.THREADS] = True
        if li:
            platforms[Platform.LINKEDIN] = True

        if not platforms:
            st.warning("Please select at least one platform.")
        else:
            row = build_content_row(
                caption=caption,
                media_url=media_url,
                platforms=platforms,
                scheduled_date=datetime.combine(scheduled_date, datetime.min.time()),
            )
            st.session_state.current_row = row

            with st.spinner("Generating AI captions..."):
                try:
                    result = generate_captions(
                        generator=st.session_state.generator,
                        row=row,
                    )
                    st.session_state.generated_captions = result
                    st.session_state.media_url = media_url
                    st.success(f"Generated captions for {len(result)} platform(s)!")
                except Exception as e:
                    st.error(f"Generation failed: {e}")

# ---------------------------------------------------------------------------
# Display generated captions (editable)
# ---------------------------------------------------------------------------

if "generated_captions" in st.session_state and st.session_state.generated_captions:
    st.divider()
    st.subheader("Generated Captions")

    captions = st.session_state.generated_captions
    for platform, caption_text in captions.items():
        with st.expander(f"{platform.value.title()}", expanded=True):
            edited = st.text_area(
                f"Edit {platform.value}",
                value=caption_text,
                key=f"edit_{platform.value}",
                height=150,
            )
            # Update in-place so edits persist
            st.session_state.generated_captions[platform] = edited

    # -----------------------------------------------------------------------
    # Re-prompt
    # -----------------------------------------------------------------------

    st.divider()
    reprompt_col1, reprompt_col2 = st.columns([3, 1])
    with reprompt_col1:
        feedback = st.text_input(
            "Re-prompt feedback (optional)",
            placeholder="Make it funnier, add more emojis...",
        )
    with reprompt_col2:
        st.write("")  # spacer
        st.write("")
        reprompt_btn = st.button("Re-generate with feedback")

    if reprompt_btn and feedback and st.session_state.generator:
        from app.helpers.create_post_helpers import regenerate_with_feedback

        with st.spinner("Re-generating with feedback..."):
            try:
                updated = regenerate_with_feedback(
                    generator=st.session_state.generator,
                    row=st.session_state.current_row,
                    feedback=feedback,
                )
                st.session_state.generated_captions = updated
                st.rerun()
            except Exception as e:
                st.error(f"Re-generation failed: {e}")

    # -----------------------------------------------------------------------
    # Send to Postiz
    # -----------------------------------------------------------------------

    st.divider()
    if st.session_state.postiz_client:
        if st.button("Send to Postiz", type="primary"):
            from app.helpers.create_post_helpers import send_to_postiz

            with st.spinner("Creating drafts in Postiz..."):
                try:
                    draft_ids = send_to_postiz(
                        postiz=st.session_state.postiz_client,
                        captions=st.session_state.generated_captions,
                        media_url=st.session_state.get("media_url") or None,
                        scheduled_at=None,
                    )
                    if draft_ids:
                        st.success(
                            f"Created {len(draft_ids)} draft(s) in Postiz! "
                            "Open Postiz to review and schedule."
                        )
                        st.session_state.generated_captions = {}
                    else:
                        st.warning("No connected platforms found in Postiz.")
                except Exception as e:
                    st.error(f"Failed to create Postiz drafts: {e}")
    else:
        st.info("Set POSTIZ_API_KEY environment variable to enable sending to Postiz.")
