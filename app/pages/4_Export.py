"""Export page — download CSV tables and Plotly charts as PNG."""

import io

import pandas as pd
import plotly.express as px
import streamlit as st

from app.stub_data import get_stub_dataframe

st.set_page_config(page_title="Export — ICT Electricity", page_icon="📤", layout="wide")
st.title("📤 Export")
st.markdown("Download model outputs as CSV or charts as PNG for use in reports and presentations.")


@st.cache_data
def load_data() -> pd.DataFrame:
    """Load model output data."""
    return get_stub_dataframe()


df = load_data()

# ── Sidebar ───────────────────────────────────────────────────────────────────

st.sidebar.header("Export Filters")
scenarios = st.sidebar.multiselect("Scenarios", sorted(df["scenario_id"].unique()), default=sorted(df["scenario_id"].unique()))
segments = st.sidebar.multiselect("Segments", sorted(df["segment"].unique()), default=sorted(df["segment"].unique()))
years = sorted(df["year"].unique())
year_range = st.sidebar.select_slider("Year range", options=years, value=(min(years), max(years)))

filtered = df[
    (df["scenario_id"].isin(scenarios))
    & (df["segment"].isin(segments))
    & (df["year"] >= year_range[0])
    & (df["year"] <= year_range[1])
]

st.info(f"**{len(filtered):,} rows** match current filters across {filtered['geo'].nunique()} geographies.")

# ── CSV export ────────────────────────────────────────────────────────────────

st.subheader("CSV Export")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Full output table** — all columns, all rows matching filters")
    csv_full = filtered.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Download full CSV",
        data=csv_full,
        file_name="ict_electricity_demand_full.csv",
        mime="text/csv",
    )

with col2:
    st.markdown("**Summary table** — TWh by geo × segment × year × scenario")
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
    csv_summary = summary.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Download summary CSV",
        data=csv_summary,
        file_name="ict_electricity_demand_summary.csv",
        mime="text/csv",
    )

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
    fig = px.line(ts, x="year", y="TWh", color="scenario_id", markers=True,
                  title="Total ICT Electricity Demand by Scenario",
                  labels={"TWh": "Electricity (TWh)", "year": "Year", "scenario_id": "Scenario"})

elif chart_type == "DC Demand by Scenario":
    dc = filtered[filtered["segment"] == "datacentres"]
    ts = dc.groupby(["year", "scenario_id"])["kwh_p50"].sum().reset_index()
    ts["TWh"] = ts["kwh_p50"] / 1e9
    fig = px.line(ts, x="year", y="TWh", color="scenario_id", markers=True,
                  title="Data Centre Electricity Demand (P50) by Scenario",
                  labels={"TWh": "Electricity (TWh)", "year": "Year", "scenario_id": "Scenario"})

else:
    latest = filtered["year"].max()
    geo_agg = (
        filtered[filtered["year"] == latest]
        .groupby("geo")["kwh_estimate"].sum().reset_index()
        .sort_values("kwh_estimate", ascending=False).head(15)
    )
    geo_agg["TWh"] = geo_agg["kwh_estimate"] / 1e9
    fig = px.bar(geo_agg, x="TWh", y="geo", orientation="h",
                 color="TWh", color_continuous_scale="Reds",
                 title=f"Top 15 Geographies by ICT Electricity ({latest})",
                 labels={"TWh": "Electricity (TWh)", "geo": "Geography"})
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, coloraxis_showscale=False)

st.plotly_chart(fig, use_container_width=True)

img_bytes = fig.to_image(format="png", width=1200, height=600, scale=2)
st.download_button(
    label="⬇️ Download chart as PNG",
    data=img_bytes,
    file_name=f"ict_electricity_{chart_type.lower().replace(' ', '_')}.png",
    mime="image/png",
)

st.divider()

# ── Data preview ──────────────────────────────────────────────────────────────

with st.expander("Preview summary table"):
    st.dataframe(summary.head(100), use_container_width=True)
