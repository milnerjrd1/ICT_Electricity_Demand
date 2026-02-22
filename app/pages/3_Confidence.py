"""Confidence page — colour-coded confidence tiers with drill-down to data quality."""

import pandas as pd
import plotly.express as px
import streamlit as st

from app.stub_data import get_stub_dataframe
from app.theme import (
    AMBER,
    CARD_BG,
    MATRIX_GREEN,
    NEON_RED,
    SEGMENT_COLORS,
    TEXT_DIM,
    TEXT_SECONDARY,
    TIER_COLORS,
    apply_matrix_theme,
    matrix_header,
    _hex_to_rgb,
)

st.set_page_config(page_title="Confidence — ICT Electricity", page_icon="🎯", layout="wide")
apply_matrix_theme()

st.markdown(
    matrix_header(
        "🎯 CONFIDENCE LENS",
        "Every output cell carries a confidence tier (1–3) · source quality · coverage · triangulation",
    ),
    unsafe_allow_html=True,
)

_TIER_LABELS = {1: "TIER 1 — HIGH", 2: "TIER 2 — MEDIUM", 3: "TIER 3 — LOW"}
_TIER_DESCRIPTIONS = {
    1: "Official statistics / regulator data. >80% segment coverage. 3+ independent sources agree within 15%.",
    2: "Industry reports / surveys. 40–80% coverage. 2 sources agree within 25%.",
    3: "Estimates / proxies. <40% coverage or single source. High sensitivity to assumptions.",
}
_TIER_BAND = {1: "±10%", 2: "±20%", 3: "±35%"}


@st.cache_data
def load_data() -> pd.DataFrame:
    """Load model output data."""
    return get_stub_dataframe()


df = load_data()

# ── Sidebar ───────────────────────────────────────────────────────────────────

st.sidebar.markdown("## ⚙ FILTERS")
scenario = st.sidebar.selectbox("Scenario", sorted(df["scenario_id"].unique()))
year = st.sidebar.selectbox("Year", sorted(df["year"].unique(), reverse=True))

filtered = df[(df["scenario_id"] == scenario) & (df["year"] == year)]

# ── Tier cards ────────────────────────────────────────────────────────────────

col1, col2, col3 = st.columns(3)
for col, tier in zip([col1, col2, col3], [1, 2, 3]):
    color = TIER_COLORS[tier]
    rgb = _hex_to_rgb(color)
    n_rows = len(filtered[filtered["confidence_tier"] == tier])
    twh = filtered[filtered["confidence_tier"] == tier]["kwh_estimate"].sum() / 1e9
    with col:
        st.markdown(
            f"""
            <div style="
                background:{CARD_BG};
                border:1px solid rgba({rgb},0.35);
                border-top:3px solid {color};
                border-radius:6px;
                padding:18px 20px;
                box-shadow:0 0 20px rgba({rgb},0.08);
            ">
                <div style="color:{color};font-size:0.75rem;font-weight:700;letter-spacing:0.12em;margin-bottom:8px;">
                    {_TIER_LABELS[tier]}
                </div>
                <div style="color:{color};font-size:1.6rem;font-weight:700;text-shadow:0 0 10px rgba({rgb},0.4);margin-bottom:4px;">
                    {n_rows:,} cells
                </div>
                <div style="color:{TEXT_DIM};font-size:0.8rem;margin-bottom:10px;">
                    {twh:,.0f} TWh · uncertainty {_TIER_BAND[tier]}
                </div>
                <div style="color:{TEXT_SECONDARY};font-size:0.78rem;line-height:1.5;border-top:1px solid rgba({rgb},0.15);padding-top:8px;">
                    {_TIER_DESCRIPTIONS[tier]}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.divider()

# ── Coverage heatmap: geo × segment ──────────────────────────────────────────

st.subheader(f"Confidence Heatmap — Geography × Segment ({year})")

pivot = (
    filtered.groupby(["geo", "segment"])["confidence_tier"]
    .mean()
    .reset_index()
    .pivot(index="geo", columns="segment", values="confidence_tier")
)

if not pivot.empty:
    fig = px.imshow(
        pivot,
        color_continuous_scale=[
            [0.0, "#0D0D0D"],
            [0.25, MATRIX_GREEN],
            [0.6, AMBER],
            [1.0, NEON_RED],
        ],
        zmin=1,
        zmax=3,
        labels={"color": "Avg Confidence Tier"},
        title=f"Average Confidence Tier by Geography × Segment ({year})",
        aspect="auto",
        text_auto=".1f",
    )
    fig.update_coloraxes(
        colorbar_tickvals=[1, 2, 3],
        colorbar_ticktext=["1 High", "2 Med", "3 Low"],
        colorbar_title_text="Tier",
    )
    fig.update_traces(textfont_color="white")
    st.plotly_chart(fig, use_container_width=True)

# ── Two-column lower section ──────────────────────────────────────────────────

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Uncertainty Band by Segment")

    fig2 = px.box(
        filtered,
        x="segment",
        y="uncertainty_band",
        color="segment",
        color_discrete_map=SEGMENT_COLORS,
        labels={"uncertainty_band": "Uncertainty Band (fractional ±)", "segment": "Segment"},
        title="Uncertainty Band Distribution",
    )
    fig2.update_layout(showlegend=False)
    st.plotly_chart(fig2, use_container_width=True)

with col_right:
    st.subheader("Average Confidence Tier by Geography")

    geo_conf = (
        filtered.groupby("geo")["confidence_tier"]
        .mean()
        .reset_index()
        .sort_values("confidence_tier")
    )

    fig3 = px.bar(
        geo_conf,
        x="geo",
        y="confidence_tier",
        color="confidence_tier",
        color_continuous_scale=[
            [0.0, MATRIX_GREEN],
            [0.5, AMBER],
            [1.0, NEON_RED],
        ],
        range_color=[1, 3],
        labels={"confidence_tier": "Avg Confidence Tier", "geo": "Geography"},
        title="Avg Confidence Tier by Geography",
    )
    fig3.update_coloraxes(showscale=False)
    fig3.add_hline(
        y=2,
        line_dash="dash",
        line_color="rgba(0,229,255,0.4)",
        annotation_text="Tier 2 threshold",
        annotation_font_color=TEXT_DIM,
    )
    st.plotly_chart(fig3, use_container_width=True)

# ── Tier methodology ──────────────────────────────────────────────────────────

with st.expander("📐 Confidence tier methodology"):
    st.markdown(
        """
        | Factor | Tier 1 — High | Tier 2 — Medium | Tier 3 — Low |
        |---|---|---|---|
        | **Source quality** | Official stats / regulator data | Industry reports / surveys | Estimates / expert judgment |
        | **Coverage** | >80% of segment covered | 40–80% covered | <40% or pure proxy |
        | **Triangulation** | 3+ sources agree within 15% | 2 sources agree within 25% | Single source or >25% divergence |
        | **Sensitivity** | Output stable (±10%) | Moderate sensitivity (±10–30%) | High sensitivity (>30% swing) |
        | **Uncertainty band** | ±10% | ±20% | ±35% |
        """
    )
