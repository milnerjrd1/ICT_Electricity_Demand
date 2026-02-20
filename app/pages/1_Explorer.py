"""Explorer page — interactive drill-down by geography × segment × product × year."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.stub_data import get_stub_dataframe

st.set_page_config(page_title="Explorer — ICT Electricity", page_icon="🔍", layout="wide")
st.title("🔍 Demand Explorer")
st.markdown("Drill down into ICT electricity demand by geography, segment, product, and year.")


@st.cache_data
def load_data() -> pd.DataFrame:
    """Load model output data."""
    return get_stub_dataframe()


df = load_data()

# ── Sidebar filters ───────────────────────────────────────────────────────────

st.sidebar.header("Explorer Filters")

scenario = st.sidebar.selectbox("Scenario", sorted(df["scenario_id"].unique()))
segments = st.sidebar.multiselect("Segments", sorted(df["segment"].unique()), default=sorted(df["segment"].unique()))
geos = st.sidebar.multiselect(
    "Geographies",
    sorted(df["geo"].unique()),
    default=[g for g in ["US", "CN", "DE", "GB", "JP", "IN", "IE", "NL", "SG", "AE"] if g in df["geo"].unique()],
)
years = sorted(df["year"].unique())
year_range = st.sidebar.select_slider("Year range", options=years, value=(min(years), max(years)))

filtered = df[
    (df["scenario_id"] == scenario)
    & (df["segment"].isin(segments))
    & (df["geo"].isin(geos))
    & (df["year"] >= year_range[0])
    & (df["year"] <= year_range[1])
]

# ── Time series ───────────────────────────────────────────────────────────────

st.subheader("Electricity Demand Over Time")

tab1, tab2, tab3 = st.tabs(["By Segment", "By Geography", "By Product"])

with tab1:
    ts_seg = filtered.groupby(["year", "segment"])["kwh_estimate"].sum().reset_index()
    ts_seg["TWh"] = ts_seg["kwh_estimate"] / 1e9
    fig = px.line(ts_seg, x="year", y="TWh", color="segment",
                  color_discrete_map={"datacentres": "#EF4444", "networks": "#3B82F6", "devices": "#10B981"},
                  markers=True, labels={"TWh": "TWh", "year": "Year"})
    fig.update_layout(hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    ts_geo = filtered.groupby(["year", "geo"])["kwh_estimate"].sum().reset_index()
    ts_geo["TWh"] = ts_geo["kwh_estimate"] / 1e9
    fig2 = px.line(ts_geo, x="year", y="TWh", color="geo", markers=True,
                   labels={"TWh": "TWh", "year": "Year"})
    fig2.update_layout(hovermode="x unified")
    st.plotly_chart(fig2, use_container_width=True)

with tab3:
    ts_prod = filtered.groupby(["year", "product"])["kwh_estimate"].sum().reset_index()
    ts_prod["TWh"] = ts_prod["kwh_estimate"] / 1e9
    fig3 = px.line(ts_prod, x="year", y="TWh", color="product", markers=True,
                   labels={"TWh": "TWh", "year": "Year"})
    fig3.update_layout(hovermode="x unified")
    st.plotly_chart(fig3, use_container_width=True)

# ── Uncertainty bands (DC only) ───────────────────────────────────────────────

st.subheader("Uncertainty Bands — Data Centres (P10/P50/P90)")

dc_filtered = filtered[filtered["segment"] == "datacentres"]
if not dc_filtered.empty:
    dc_ts = dc_filtered.groupby("year").agg(
        kwh_p10=("kwh_p10", "sum"),
        kwh_p50=("kwh_p50", "sum"),
        kwh_p90=("kwh_p90", "sum"),
    ).reset_index()

    fig4 = go.Figure()
    fig4.add_trace(go.Scatter(
        x=dc_ts["year"], y=dc_ts["kwh_p90"] / 1e9,
        fill=None, mode="lines", line=dict(color="rgba(239,68,68,0.3)"), name="P90",
    ))
    fig4.add_trace(go.Scatter(
        x=dc_ts["year"], y=dc_ts["kwh_p10"] / 1e9,
        fill="tonexty", mode="lines", line=dict(color="rgba(239,68,68,0.3)"),
        fillcolor="rgba(239,68,68,0.1)", name="P10",
    ))
    fig4.add_trace(go.Scatter(
        x=dc_ts["year"], y=dc_ts["kwh_p50"] / 1e9,
        mode="lines", line=dict(color="#EF4444", width=2), name="P50",
    ))
    fig4.update_layout(
        xaxis_title="Year", yaxis_title="TWh",
        title="Data Centre Electricity — P10/P50/P90 Uncertainty Bands",
        hovermode="x unified",
    )
    st.plotly_chart(fig4, use_container_width=True)
else:
    st.info("No data centre data for selected filters.")

# ── Data table ────────────────────────────────────────────────────────────────

with st.expander("Raw data table"):
    display = filtered.copy()
    for col in ["kwh_estimate", "kwh_p10", "kwh_p50", "kwh_p90"]:
        display[col] = (display[col] / 1e9).round(3)
    display = display.rename(columns={
        "kwh_estimate": "TWh_estimate", "kwh_p10": "TWh_p10",
        "kwh_p50": "TWh_p50", "kwh_p90": "TWh_p90",
    })
    st.dataframe(display, use_container_width=True)
