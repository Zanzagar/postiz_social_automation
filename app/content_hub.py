"""Streamlit Content Hub — staff-facing UI for content management."""

import streamlit as st

st.set_page_config(
    page_title="Gita Valley Content Hub",
    page_icon="\U0001f404",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Sidebar branding
with st.sidebar:
    st.title("Content Hub")
    st.markdown("---")
    st.markdown("**Gita Valley**")
    st.markdown("*Cultivating Soil and Soul*")

# Main dashboard
st.title("Gita Valley Content Hub")
st.markdown("Create, review, and schedule social media content for Gita Valley.")

# Quick stats
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Pending Drafts", "--")
with col2:
    st.metric("This Week's Posts", "--")
with col3:
    st.metric("Engagement Rate", "--")
