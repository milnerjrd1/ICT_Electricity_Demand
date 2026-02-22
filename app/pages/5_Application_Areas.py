"""Application Areas page — drill-down by application area and product group.

Aligned with the Fraunhofer Green ICT @ FMD study taxonomy:
  - Households
  - Workplace
  - Public Spaces
  - Data Centres
  - Telecom Networks
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.stub_data import get_stub_dataframe
from app.theme import (
    AMBER,
    CARD_BG,
    CYAN,
    CYAN_GLOW,
    MATRIX_GREEN,
    MATRIX_GREEN_GLOW,
    NEON_RED,
    NEON_RED_GLOW,
    TEXT_DIM,
    TEXT_SECONDARY,
    apply_matrix_theme,
    matrix_header,
    matrix_kpi_card,
)
from src.models.taxonomy import APPLICATION_AREAS, enrich_with_taxonomy

st.set_page_config(
    page_title="Application Areas — ICT Electricity",
    page_icon="🏗",
    layout="wide",
)
apply_matrix_theme()

st.markdown(
    matrix_header(
        "🏗 APPLICATION AREAS",
        "Fraunhofer taxonomy · households · workplace · public spaces · data centres · telecom",
    ),
    unsafe_allow_html=True,
)

# ── Colour map for application areas ─────────────────────────────────────────

AREA_COLORS = {
    "households":       MATRIX_GREEN,
    "workplace":        CYAN,
    "public_spaces":    AMBER,
    "datacentres":      NEON_RED,
    "telecom_networks": "#AA00FF",
}

AREA_LABELS = {
    "households":       "Households",
    "workplace":        "Workplace",
    "public_spaces":    "Public Spaces",
    "datacentres":      "Data Centres",
    "telecom_networks": "Telecom Networks",
}


@st.cache_data
def load_data() -> pd.DataFrame:
    """Load and enrich stub data with taxonomy dimensions."""
    df = get_stub_dataframe()
    df = enrich_with_taxonomy(df)
    return df


df = load_data()

# ── Sidebar filters ───────────────────────────────────────────────────────────

st.sidebar.markdown("## ⚙ AREA FILTERS")

scenario = st.sidebar.selectbox("Scenario", sorted(df["scenario_id"].unique()))

all_areas = sorted(df["application_area"].unique())
selected_areas = st.sidebar.multiselect(
    "Application Areas",
    options=all_areas,
    default=all_areas,
    format_func=lambda a: AREA_LABELS.get(a, a),
)

geos = st.sidebar.multiselect(
    "Geographies",
    sorted(df["geo"].unique()),
    default=[g for g in ["US", "CN", "DE", "GB", "JP"] if g in df["geo"].unique()],
)

years = sorted(df["year"].unique())
year_range = st.sidebar.select_slider(
    "Year range", options=years, value=(min(years), max(years))
)

filtered = df[
    (df["scenario_id"] == scenario)
    & (df["application_area"].isin(selected_areas))
    & (df["geo"].isin(geos))
    & (df["year"] >= year_range[0])
    & (df["year"] <= year_range[1])
]

# ── KPI row ───────────────────────────────────────────────────────────────────

latest_year = filtered["year"].max() if not filtered.empty else year_range[1]
latest = filtered[filtered["year"] == latest_year]

total_twh = latest["kwh_estimate"].sum() / 1e9
n_areas = latest["application_area"].nunique()
n_products = latest["product_group"].nunique() if "product_group" in latest.columns else 0

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(
        matrix_kpi_card("Total ICT", f"{total_twh:,.1f} TWh", f"all areas · {latest_year}"),
        unsafe_allow_html=True,
    )
with k2:
    st.markdown(
        matrix_kpi_card("Areas Selected", str(n_areas), "application areas", color=CYAN),
        unsafe_allow_html=True,
    )
with k3:
    st.markdown(
        matrix_kpi_card("Product Groups", str(n_products), "in scope", color=AMBER),
        unsafe_allow_html=True,
    )
with k4:
    hh_twh = latest[latest["application_area"] == "households"]["kwh_estimate"].sum() / 1e9
    dc_twh = latest[latest["application_area"] == "datacentres"]["kwh_estimate"].sum() / 1e9
    ratio = f"{dc_twh / hh_twh:.2f}×" if hh_twh > 0 else "—"
    st.markdown(
        matrix_kpi_card("DC / Households", ratio, "electricity intensity ratio", color=NEON_RED),
        unsafe_allow_html=True,
    )

st.divider()

# ── Time series by application area ──────────────────────────────────────────

st.subheader("Electricity Demand by Application Area")

tab1, tab2, tab3 = st.tabs(["Time Series", "Area Composition", "Product Groups"])

with tab1:
    ts = (
        filtered.groupby(["year", "application_area"])["kwh_estimate"]
        .sum()
        .reset_index()
    )
    ts["TWh"] = ts["kwh_estimate"] / 1e9
    ts["Area"] = ts["application_area"].map(AREA_LABELS)

    fig = px.line(
        ts,
        x="year",
        y="TWh",
        color="application_area",
        color_discrete_map=AREA_COLORS,
        markers=True,
        labels={"TWh": "TWh", "year": "Year", "application_area": "Application Area"},
        title=f"ICT Electricity by Application Area — {scenario}",
        custom_data=["Area"],
    )
    fig.update_traces(
        line_width=2.5,
        marker_size=6,
        hovertemplate="<b>%{customdata[0]}</b><br>Year: %{x}<br>%{y:.2f} TWh<extra></extra>",
    )
    fig.update_layout(hovermode="x unified", legend_title="Application Area")
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    ref_years = [y for y in [2020, 2025, 2030, 2035] if y in filtered["year"].values]
    if not ref_years:
        ref_years = [latest_year]

    comp = (
        filtered[filtered["year"].isin(ref_years)]
        .groupby(["year", "application_area"])["kwh_estimate"]
        .sum()
        .reset_index()
    )
    comp["TWh"] = comp["kwh_estimate"] / 1e9
    comp["Area"] = comp["application_area"].map(AREA_LABELS)

    fig2 = px.bar(
        comp,
        x="year",
        y="TWh",
        color="application_area",
        color_discrete_map=AREA_COLORS,
        barmode="stack",
        labels={"TWh": "TWh", "year": "Year", "application_area": "Application Area"},
        title="Application Area Composition at Reference Years",
        custom_data=["Area"],
    )
    fig2.update_traces(
        hovertemplate="<b>%{customdata[0]}</b><br>Year: %{x}<br>%{y:.2f} TWh<extra></extra>",
    )
    fig2.update_layout(legend_title="Application Area")
    st.plotly_chart(fig2, use_container_width=True)

with tab3:
    pg_col = "product_group" if "product_group" in filtered.columns else "product"
    pg_ts = (
        filtered.groupby(["year", "application_area", pg_col])["kwh_estimate"]
        .sum()
        .reset_index()
    )
    pg_ts["TWh"] = pg_ts["kwh_estimate"] / 1e9

    area_choice = st.selectbox(
        "Select application area",
        options=selected_areas,
        format_func=lambda a: AREA_LABELS.get(a, a),
    )
    pg_filtered = pg_ts[pg_ts["application_area"] == area_choice]

    if not pg_filtered.empty:
        fig3 = px.line(
            pg_filtered,
            x="year",
            y="TWh",
            color=pg_col,
            markers=True,
            labels={"TWh": "TWh", "year": "Year", pg_col: "Product Group"},
            title=f"Product Groups — {AREA_LABELS.get(area_choice, area_choice)}",
        )
        fig3.update_traces(line_width=2, marker_size=5)
        fig3.update_layout(hovermode="x unified")
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("No data for selected area and filters.")

st.divider()

# ── Share treemap ─────────────────────────────────────────────────────────────

st.subheader(f"Demand Share — {latest_year}")

treemap_year = st.select_slider(
    "Treemap year",
    options=sorted(filtered["year"].unique()),
    value=latest_year,
    key="treemap_year",
)

pg_col = "product_group" if "product_group" in filtered.columns else "product"
tree_data = (
    filtered[filtered["year"] == treemap_year]
    .groupby(["application_area", pg_col])["kwh_estimate"]
    .sum()
    .reset_index()
)
tree_data["TWh"] = tree_data["kwh_estimate"] / 1e9
tree_data["Area Label"] = tree_data["application_area"].map(AREA_LABELS)

if not tree_data.empty:
    fig4 = px.treemap(
        tree_data,
        path=["Area Label", pg_col],
        values="TWh",
        color="application_area",
        color_discrete_map=AREA_COLORS,
        title=f"ICT Electricity Share by Application Area × Product Group ({treemap_year})",
    )
    fig4.update_traces(
        textinfo="label+percent root",
        hovertemplate="<b>%{label}</b><br>%{value:.2f} TWh<br>%{percentRoot:.1%} of total<extra></extra>",
    )
    st.plotly_chart(fig4, use_container_width=True)
else:
    st.info("No data for selected year.")

st.divider()

# ── Data table ────────────────────────────────────────────────────────────────

with st.expander("📋 Raw data — application area breakdown"):
    display = (
        filtered.groupby(["geo", "application_area", pg_col, "year"])["kwh_estimate"]
        .sum()
        .reset_index()
    )
    display["TWh"] = (display["kwh_estimate"] / 1e9).round(4)
    display["Area"] = display["application_area"].map(AREA_LABELS)
    display = display.drop(columns=["kwh_estimate"]).rename(columns={pg_col: "product_group"})
    st.dataframe(display, use_container_width=True)
