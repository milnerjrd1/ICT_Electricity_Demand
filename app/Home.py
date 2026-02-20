"""ICT Electricity Demand — Streamlit Home page.

Entry point for the decision-support tool.
Loads stub data conforming to OutputSchema and displays a summary dashboard.
"""

import logging

import pandas as pd
import plotly.express as px
import streamlit as st

from src.models.schema import REQUIRED_COLUMNS, validate_output
from app.stub_data import get_stub_dataframe

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="ICT Electricity Demand",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("⚡ Global ICT Electricity Demand")
st.markdown(
    """
    A modular model and decision-support tool estimating ICT-driven electricity demand
    by **geography × segment × product × year** — with emissions, cost overlays,
    and explicit uncertainty quantification.
    """
)

st.info(
    "**Status: Phase 0 — Scaffold complete.** "
    "This view uses stub data. Real model outputs will appear as data loaders and model modules are built.",
    icon="🔧",
)

# ── Load data ────────────────────────────────────────────────────────────────

@st.cache_data
def load_data() -> pd.DataFrame:
    """Load model output data (stub during Phase 0)."""
    return get_stub_dataframe()


df = load_data()

# ── Sidebar filters ───────────────────────────────────────────────────────────

st.sidebar.header("Filters")

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

col1, col2, col3, col4 = st.columns(4)

latest_year = filtered["year"].max() if not filtered.empty else "—"
total_twh = filtered[filtered["year"] == latest_year]["kwh_estimate"].sum() / 1e9 if not filtered.empty else 0.0
dc_twh = (
    filtered[(filtered["year"] == latest_year) & (filtered["segment"] == "datacentres")]["kwh_estimate"].sum() / 1e9
    if not filtered.empty
    else 0.0
)
n_geos = filtered["geo"].nunique() if not filtered.empty else 0

col1.metric("Total ICT Electricity", f"{total_twh:,.0f} TWh", help=f"Year: {latest_year}")
col2.metric("Data Centre Share", f"{dc_twh / total_twh:.0%}" if total_twh > 0 else "—", help="DC as % of total ICT")
col3.metric("Geographies Covered", n_geos)
col4.metric("Scenario", selected_scenario)

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
        color_discrete_map={
            "datacentres": "#EF4444",
            "networks": "#3B82F6",
            "devices": "#10B981",
        },
        labels={"TWh": "Electricity (TWh)", "year": "Year"},
        title=f"ICT Electricity Demand — {selected_scenario}",
    )
    fig.update_layout(hovermode="x unified", legend_title="Segment")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("No data for selected filters.")

# ── Top geographies ───────────────────────────────────────────────────────────

st.subheader(f"Top Geographies by ICT Electricity ({latest_year})")

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
        color_continuous_scale="Reds",
        labels={"TWh": "Electricity (TWh)", "geo": "Geography"},
        title=f"Top 15 Geographies — {latest_year}",
    )
    fig2.update_layout(yaxis={"categoryorder": "total ascending"}, coloraxis_showscale=False)
    st.plotly_chart(fig2, use_container_width=True)

# ── Confidence tier breakdown ─────────────────────────────────────────────────

st.subheader("Output Confidence Distribution")

if not filtered.empty:
    tier_counts = filtered["confidence_tier"].value_counts().sort_index().reset_index()
    tier_counts.columns = ["confidence_tier", "count"]
    tier_counts["label"] = tier_counts["confidence_tier"].map(
        {1: "Tier 1 — High", 2: "Tier 2 — Medium", 3: "Tier 3 — Low"}
    )

    fig3 = px.pie(
        tier_counts,
        values="count",
        names="label",
        color="confidence_tier",
        color_discrete_map={1: "#10B981", 2: "#F59E0B", 3: "#EF4444"},
        title="Rows by Confidence Tier",
    )
    st.plotly_chart(fig3, use_container_width=True)

# ── Footer ────────────────────────────────────────────────────────────────────

st.divider()
st.caption(
    "ICT Electricity Demand Model — Phase 0 Scaffold | "
    "Navigate to Explorer, Scenarios, Confidence, or Export using the sidebar."
)
