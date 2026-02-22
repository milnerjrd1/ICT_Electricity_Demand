"""ICT Electricity Demand — Streamlit Home page.

Entry point for the decision-support tool.
Loads stub data conforming to OutputSchema and displays a summary dashboard.
"""

import logging

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.stub_data import get_stub_dataframe
from app.theme import (
    AMBER,
    CARD_BG,
    CYAN,
    MATRIX_GREEN,
    NEON_RED,
    SCENARIO_COLORS,
    SEGMENT_COLORS,
    TEXT_DIM,
    apply_matrix_theme,
    matrix_header,
    matrix_kpi_card,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="ICT Electricity Demand",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_matrix_theme()

# ── Header ────────────────────────────────────────────────────────────────────

st.markdown(
    matrix_header(
        "⚡ GLOBAL ICT ELECTRICITY DEMAND",
        "Modular scenario model · geography × segment × product × year · P10/P50/P90 uncertainty",
    ),
    unsafe_allow_html=True,
)

st.info(
    "**PHASE 0 — STUB DATA** · Real model outputs will replace this as data loaders are built.",
    icon="🔧",
)

# ── Load data ────────────────────────────────────────────────────────────────

@st.cache_data
def load_data() -> pd.DataFrame:
    """Load model output data (stub during Phase 0)."""
    return get_stub_dataframe()


df = load_data()

# ── Sidebar filters ───────────────────────────────────────────────────────────

st.sidebar.markdown("## ⚙ FILTERS")

all_scenarios = sorted(df["scenario_id"].unique())
selected_scenario = st.sidebar.selectbox("Scenario", all_scenarios, index=0)

all_segments = sorted(df["segment"].unique())
selected_segments = st.sidebar.multiselect("Segments", all_segments, default=all_segments)

all_years = sorted(df["year"].unique())
year_range = st.sidebar.select_slider(
    "Year range",
    options=all_years,
    value=(min(all_years), max(all_years)),
)

filtered = df[
    (df["scenario_id"] == selected_scenario)
    & (df["segment"].isin(selected_segments))
    & (df["year"] >= year_range[0])
    & (df["year"] <= year_range[1])
]

# ── KPI row ───────────────────────────────────────────────────────────────────

latest_year = filtered["year"].max() if not filtered.empty else "—"
total_twh = (
    filtered[filtered["year"] == latest_year]["kwh_estimate"].sum() / 1e9
    if not filtered.empty
    else 0.0
)
dc_twh = (
    filtered[(filtered["year"] == latest_year) & (filtered["segment"] == "datacentres")][
        "kwh_estimate"
    ].sum()
    / 1e9
    if not filtered.empty
    else 0.0
)
n_geos = filtered["geo"].nunique() if not filtered.empty else 0
dc_share_str = f"{dc_twh / total_twh:.0%}" if total_twh > 0 else "—"

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
with kpi1:
    st.markdown(
        matrix_kpi_card("Total ICT Electricity", f"{total_twh:,.0f} TWh", f"Year: {latest_year}"),
        unsafe_allow_html=True,
    )
with kpi2:
    st.markdown(
        matrix_kpi_card("Data Centre Share", dc_share_str, "% of total ICT", color=NEON_RED),
        unsafe_allow_html=True,
    )
with kpi3:
    st.markdown(
        matrix_kpi_card("Geographies", str(n_geos), "countries / regions", color=CYAN),
        unsafe_allow_html=True,
    )
with kpi4:
    st.markdown(
        matrix_kpi_card("Active Scenario", selected_scenario.replace("_", " ").upper(), "", color=AMBER),
        unsafe_allow_html=True,
    )

st.divider()

# ── Time series by segment ────────────────────────────────────────────────────

st.subheader("ICT Electricity Demand by Segment")

if not filtered.empty:
    ts = (
        filtered.groupby(["year", "segment"])["kwh_estimate"]
        .sum()
        .reset_index()
    )
    ts["TWh"] = ts["kwh_estimate"] / 1e9

    fig = px.area(
        ts,
        x="year",
        y="TWh",
        color="segment",
        color_discrete_map=SEGMENT_COLORS,
        labels={"TWh": "Electricity (TWh)", "year": "Year"},
        title=f"ICT Electricity Demand — {selected_scenario.replace('_', ' ').upper()}",
    )
    fig.update_traces(line_width=2)
    fig.update_layout(hovermode="x unified", legend_title="Segment")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("No data for selected filters.")

# ── Two-column lower section ──────────────────────────────────────────────────

col_left, col_right = st.columns([3, 2])

with col_left:
    st.subheader(f"Top Geographies — {latest_year}")

    if not filtered.empty:
        geo_agg = (
            filtered[filtered["year"] == latest_year]
            .groupby("geo")["kwh_estimate"]
            .sum()
            .reset_index()
            .sort_values("kwh_estimate", ascending=False)
            .head(15)
        )
        geo_agg["TWh"] = geo_agg["kwh_estimate"] / 1e9

        fig2 = px.bar(
            geo_agg,
            x="TWh",
            y="geo",
            orientation="h",
            color="TWh",
            color_continuous_scale=[[0, CARD_BG], [0.4, MATRIX_GREEN], [1.0, CYAN]],
            labels={"TWh": "Electricity (TWh)", "geo": "Geography"},
            title=f"Top 15 Geographies — {latest_year}",
        )
        fig2.update_layout(
            yaxis={"categoryorder": "total ascending"},
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig2, use_container_width=True)

with col_right:
    st.subheader("Confidence Distribution")

    if not filtered.empty:
        tier_counts = (
            filtered["confidence_tier"].value_counts().sort_index().reset_index()
        )
        tier_counts.columns = ["confidence_tier", "count"]
        tier_counts["label"] = tier_counts["confidence_tier"].map(
            {1: "Tier 1 — High", 2: "Tier 2 — Medium", 3: "Tier 3 — Low"}
        )

        fig3 = go.Figure(
            go.Pie(
                labels=tier_counts["label"],
                values=tier_counts["count"],
                hole=0.55,
                marker=dict(
                    colors=[
                        MATRIX_GREEN if t == 1 else AMBER if t == 2 else NEON_RED
                        for t in tier_counts["confidence_tier"]
                    ],
                    line=dict(color=CARD_BG, width=2),
                ),
                textfont=dict(color="#FFFFFF"),
            )
        )
        fig3.update_layout(
            title="Output Rows by Confidence Tier",
            showlegend=True,
            annotations=[
                dict(
                    text="CONFIDENCE",
                    x=0.5,
                    y=0.5,
                    font_size=11,
                    showarrow=False,
                    font_color=TEXT_DIM,
                )
            ],
        )
        st.plotly_chart(fig3, use_container_width=True)

# ── Footer ────────────────────────────────────────────────────────────────────

st.divider()
st.caption(
    "ICT Electricity Demand Model — Phase 0 Scaffold · "
    "Navigate via sidebar: Explorer · Scenarios · Confidence · Export"
)
