"""Export page — download CSV tables and Plotly charts as PNG."""

import pandas as pd
import plotly.express as px
import streamlit as st

from app.stub_data import get_stub_dataframe
from app.theme import (
    CARD_BG,
    CYAN,
    MATRIX_GREEN,
    NEON_RED,
    SCENARIO_COLORS,
    SEGMENT_COLORS,
    TEXT_DIM,
    TEXT_SECONDARY,
    apply_matrix_theme,
    matrix_header,
    matrix_kpi_card,
)

st.set_page_config(page_title="Export — ICT Electricity", page_icon="📤", layout="wide")
apply_matrix_theme()

st.markdown(
    matrix_header(
        "📤 EXPORT",
        "Download model outputs as CSV · charts as PNG",
    ),
    unsafe_allow_html=True,
)


@st.cache_data
def load_data() -> pd.DataFrame:
    """Load model output data."""
    return get_stub_dataframe()


df = load_data()

# ── Sidebar ───────────────────────────────────────────────────────────────────

st.sidebar.markdown("## ⚙ EXPORT FILTERS")
scenarios = st.sidebar.multiselect(
    "Scenarios", sorted(df["scenario_id"].unique()), default=sorted(df["scenario_id"].unique())
)
segments = st.sidebar.multiselect(
    "Segments", sorted(df["segment"].unique()), default=sorted(df["segment"].unique())
)
years = sorted(df["year"].unique())
year_range = st.sidebar.select_slider("Year range", options=years, value=(min(years), max(years)))

filtered = df[
    (df["scenario_id"].isin(scenarios))
    & (df["segment"].isin(segments))
    & (df["year"] >= year_range[0])
    & (df["year"] <= year_range[1])
]

# ── Status row ────────────────────────────────────────────────────────────────

k1, k2, k3 = st.columns(3)
with k1:
    st.markdown(
        matrix_kpi_card("Rows Selected", f"{len(filtered):,}", "matching current filters"),
        unsafe_allow_html=True,
    )
with k2:
    st.markdown(
        matrix_kpi_card("Geographies", str(filtered["geo"].nunique()), "countries / regions", color=CYAN),
        unsafe_allow_html=True,
    )
with k3:
    st.markdown(
        matrix_kpi_card("Scenarios", str(filtered["scenario_id"].nunique()), "selected", color=NEON_RED),
        unsafe_allow_html=True,
    )

st.divider()

# ── CSV export ────────────────────────────────────────────────────────────────

st.subheader("CSV Export")

summary = (
    filtered.groupby(["geo", "segment", "year", "scenario_id"])
    .agg(
        twh_estimate=("kwh_estimate", lambda x: x.sum() / 1e9),
        twh_p10=("kwh_p10", lambda x: x.sum() / 1e9),
        twh_p50=("kwh_p50", lambda x: x.sum() / 1e9),
        twh_p90=("kwh_p90", lambda x: x.sum() / 1e9),
        avg_confidence_tier=("confidence_tier", "mean"),
    )
    .reset_index()
    .round(4)
)

col1, col2 = st.columns(2)

with col1:
    st.markdown(
        f'<div style="background:{CARD_BG};border:1px solid rgba(0,255,65,0.15);border-radius:6px;padding:16px 20px;margin-bottom:12px;">'
        f'<div style="color:{MATRIX_GREEN};font-size:0.75rem;font-weight:700;letter-spacing:0.1em;margin-bottom:6px;">FULL OUTPUT TABLE</div>'
        f'<div style="color:{TEXT_DIM};font-size:0.82rem;margin-bottom:14px;">All columns · all rows matching filters · {len(filtered):,} rows</div>',
        unsafe_allow_html=True,
    )
    csv_full = filtered.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇ Download full CSV",
        data=csv_full,
        file_name="ict_electricity_demand_full.csv",
        mime="text/csv",
    )
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    st.markdown(
        f'<div style="background:{CARD_BG};border:1px solid rgba(0,229,255,0.15);border-radius:6px;padding:16px 20px;margin-bottom:12px;">'
        f'<div style="color:{CYAN};font-size:0.75rem;font-weight:700;letter-spacing:0.1em;margin-bottom:6px;">SUMMARY TABLE</div>'
        f'<div style="color:{TEXT_DIM};font-size:0.82rem;margin-bottom:14px;">TWh by geo × segment × year × scenario · {len(summary):,} rows</div>',
        unsafe_allow_html=True,
    )
    csv_summary = summary.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇ Download summary CSV",
        data=csv_summary,
        file_name="ict_electricity_demand_summary.csv",
        mime="text/csv",
    )
    st.markdown("</div>", unsafe_allow_html=True)

st.divider()

# ── Chart export ──────────────────────────────────────────────────────────────

st.subheader("Chart Export (PNG)")

chart_type = st.selectbox(
    "Select chart",
    ["Total ICT by Scenario", "DC Demand by Scenario", "Top Geographies"],
)

if chart_type == "Total ICT by Scenario":
    ts = filtered.groupby(["year", "scenario_id"])["kwh_estimate"].sum().reset_index()
    ts["TWh"] = ts["kwh_estimate"] / 1e9
    fig = px.line(
        ts,
        x="year",
        y="TWh",
        color="scenario_id",
        color_discrete_map=SCENARIO_COLORS,
        markers=True,
        title="Total ICT Electricity Demand by Scenario",
        labels={"TWh": "Electricity (TWh)", "year": "Year", "scenario_id": "Scenario"},
    )
    fig.update_traces(line_width=2.5, marker_size=7)

elif chart_type == "DC Demand by Scenario":
    dc = filtered[filtered["segment"] == "datacentres"]
    ts = dc.groupby(["year", "scenario_id"])["kwh_p50"].sum().reset_index()
    ts["TWh"] = ts["kwh_p50"] / 1e9
    fig = px.line(
        ts,
        x="year",
        y="TWh",
        color="scenario_id",
        color_discrete_map=SCENARIO_COLORS,
        markers=True,
        title="Data Centre Electricity Demand (P50) by Scenario",
        labels={"TWh": "Electricity (TWh)", "year": "Year", "scenario_id": "Scenario"},
    )
    fig.update_traces(line_width=2.5, marker_size=7)

else:
    latest = filtered["year"].max()
    geo_agg = (
        filtered[filtered["year"] == latest]
        .groupby("geo")["kwh_estimate"]
        .sum()
        .reset_index()
        .sort_values("kwh_estimate", ascending=False)
        .head(15)
    )
    geo_agg["TWh"] = geo_agg["kwh_estimate"] / 1e9
    fig = px.bar(
        geo_agg,
        x="TWh",
        y="geo",
        orientation="h",
        color="TWh",
        color_continuous_scale=[[0, CARD_BG], [0.4, MATRIX_GREEN], [1.0, CYAN]],
        title=f"Top 15 Geographies by ICT Electricity ({latest})",
        labels={"TWh": "Electricity (TWh)", "geo": "Geography"},
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, coloraxis_showscale=False)

fig.update_layout(hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

img_bytes = fig.to_image(format="png", width=1400, height=700, scale=2)
st.download_button(
    label="⬇ Download chart as PNG",
    data=img_bytes,
    file_name=f"ict_electricity_{chart_type.lower().replace(' ', '_')}.png",
    mime="image/png",
)

st.divider()

# ── Data preview ──────────────────────────────────────────────────────────────

with st.expander("📋 Preview summary table"):
    st.dataframe(summary.head(100), use_container_width=True)
