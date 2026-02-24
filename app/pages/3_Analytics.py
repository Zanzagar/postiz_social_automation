"""Analytics page — track post performance and content intelligence."""

from pathlib import Path

import streamlit as st

from app.pages.dashboard_helpers import (
    build_pillar_comparison,
    compute_metrics,
    load_dashboard_data,
    load_performance_posts,
)

st.set_page_config(page_title="Analytics", page_icon="\U0001f4ca", layout="wide")

st.title("Performance Dashboard")
st.markdown("Track post performance, engagement trends, and content intelligence.")

data_dir = Path("data")

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

context = load_dashboard_data(data_dir=data_dir)
posts = load_performance_posts(data_dir=data_dir)
metrics = compute_metrics(posts)

# ---------------------------------------------------------------------------
# Key metrics
# ---------------------------------------------------------------------------

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Avg Engagement", f"{metrics['avg_engagement']:.1%}")
with col2:
    st.metric("Total Posts", metrics["total_posts"])
with col3:
    st.metric("Total Reach", f"{metrics['total_reach']:,}")
with col4:
    top_pillars = context.get("top_performing_pillars", [])
    st.metric("Top Pillar", top_pillars[0] if top_pillars else "N/A")

# ---------------------------------------------------------------------------
# Pillar distribution chart
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Content Pillar Distribution")

pillar_dist = context.get("pillar_distribution", {})
comparison = build_pillar_comparison(pillar_dist)

if comparison:
    import pandas as pd

    df = pd.DataFrame(comparison)
    df = df.set_index("pillar")
    st.bar_chart(df[["target", "actual"]])
else:
    st.info("No pillar distribution data available yet.")

# ---------------------------------------------------------------------------
# AI Insights
# ---------------------------------------------------------------------------

st.divider()
st.subheader("AI Insights")

insights = context.get("insights", [])
if insights:
    for insight in insights:
        st.info(insight)
else:
    st.info("No insights available. Run the learning pipeline to collect engagement data.")

# ---------------------------------------------------------------------------
# Last updated
# ---------------------------------------------------------------------------

last_updated = context.get("last_updated", "Never")
st.caption(f"Last updated: {last_updated}")
