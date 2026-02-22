"""Appendix Export page — study-aligned appendix tables with CSV download.

Produces the three appendix tables from src/models/reporting.py:
  1. Per product group × metric × reference year (appendix_table)
  2. Totals by application area × reference year (by_application_area)
  3. Overall ICT totals × reference year (total_ict)

All tables can be downloaded as CSV.
"""

import io

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
    TEXT_DIM,
    apply_matrix_theme,
    matrix_header,
    matrix_kpi_card,
)
from src.models.reporting import build_full_report
from src.models.taxonomy import enrich_with_taxonomy

st.set_page_config(
    page_title="Appendix Export — ICT Electricity",
    page_icon="📑",
    layout="wide",
)
apply_matrix_theme()

st.markdown(
    matrix_header(
        "📑 APPENDIX EXPORT",
        "Study-aligned output tables · per product group · application area · reference years",
    ),
    unsafe_allow_html=True,
)

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
def load_enriched_data() -> pd.DataFrame:
    """Load stub data enriched with taxonomy dimensions."""
    df = get_stub_dataframe()
    df = enrich_with_taxonomy(df)
    # Stub data has no emissions — add a synthetic column for demo
    df["emissions_kgco2e"] = df["kwh_estimate"] * 0.35
    df["emissions_p10_kgco2e"] = df["kwh_p10"] * 0.35
    df["emissions_p50_kgco2e"] = df["kwh_p50"] * 0.35
    df["emissions_p90_kgco2e"] = df["kwh_p90"] * 0.35
    return df


df_all = load_enriched_data()

# ── Sidebar controls ──────────────────────────────────────────────────────────

st.sidebar.markdown("## ⚙ APPENDIX SETTINGS")

scenario = st.sidebar.selectbox("Scenario", sorted(df_all["scenario_id"].unique()))

available_years = sorted(df_all["year"].unique())
ref_year_options = [y for y in available_years if y % 5 == 0]
if not ref_year_options:
    ref_year_options = available_years[:3]

default_ref_years = [y for y in [2020, 2025, 2030, 2035] if y in ref_year_options]
if not default_ref_years:
    default_ref_years = ref_year_options[:3]

reference_years = st.sidebar.multiselect(
    "Reference years",
    options=ref_year_options,
    default=default_ref_years,
)

geos = st.sidebar.multiselect(
    "Geographies",
    sorted(df_all["geo"].unique()),
    default=[g for g in ["US", "CN", "DE", "GB", "JP"] if g in df_all["geo"].unique()],
)

if not reference_years:
    st.warning("Select at least one reference year in the sidebar.")
    st.stop()

# ── Filter and build report ───────────────────────────────────────────────────

df_filtered = df_all[
    (df_all["scenario_id"] == scenario)
    & (df_all["geo"].isin(geos))
]


@st.cache_data
def build_report(scenario_id: str, geo_list: tuple, ref_years: tuple) -> dict:
    """Build appendix report (cached by scenario + geo + ref years)."""
    sub = df_all[
        (df_all["scenario_id"] == scenario_id)
        & (df_all["geo"].isin(list(geo_list)))
    ]
    return build_full_report(sub, reference_years=list(ref_years))


report = build_report(scenario, tuple(sorted(geos)), tuple(sorted(reference_years)))

appendix_df = report.get("appendix_table", pd.DataFrame())
by_area_df  = report.get("by_application_area", pd.DataFrame())
total_df    = report.get("total_ict", pd.DataFrame())

# ── KPI row ───────────────────────────────────────────────────────────────────

if not total_df.empty and reference_years:
    latest_ref = max(reference_years)
    latest_row = total_df[total_df["year"] == latest_ref]
    total_twh = latest_row["kwh_twh"].iloc[0] if not latest_row.empty else 0.0
    total_em  = latest_row["emissions_mtco2e"].iloc[0] if (not latest_row.empty and "emissions_mtco2e" in latest_row.columns) else 0.0
else:
    total_twh, total_em, latest_ref = 0.0, 0.0, max(reference_years) if reference_years else "—"

n_pg = appendix_df["product_group"].nunique() if not appendix_df.empty else 0

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(
        matrix_kpi_card("Total ICT", f"{total_twh:,.1f} TWh", f"all areas · {latest_ref}"),
        unsafe_allow_html=True,
    )
with k2:
    st.markdown(
        matrix_kpi_card("Emissions", f"{total_em:,.2f} MtCO₂e", f"reference · {latest_ref}", color=NEON_RED),
        unsafe_allow_html=True,
    )
with k3:
    st.markdown(
        matrix_kpi_card("Product Groups", str(n_pg), "in appendix table", color=CYAN),
        unsafe_allow_html=True,
    )
with k4:
    st.markdown(
        matrix_kpi_card("Reference Years", str(len(reference_years)), "selected", color=AMBER),
        unsafe_allow_html=True,
    )

st.divider()

# ── Table 1: Total ICT ────────────────────────────────────────────────────────

st.subheader("Table A — Total ICT Electricity & Emissions")

if not total_df.empty:
    display_total = total_df.copy()
    for col in display_total.columns:
        if col != "year" and display_total[col].dtype in [float]:
            display_total[col] = display_total[col].round(3)

    st.dataframe(display_total, use_container_width=True, hide_index=True)

    col1, col2 = st.columns(2)
    with col1:
        fig_total = go.Figure()
        fig_total.add_trace(go.Bar(
            x=total_df["year"].astype(str),
            y=total_df["kwh_twh"],
            name="Central (P50)",
            marker_color=MATRIX_GREEN,
            error_y=dict(
                type="data",
                symmetric=False,
                array=(total_df["kwh_p90_twh"] - total_df["kwh_twh"]).tolist()
                    if "kwh_p90_twh" in total_df.columns else None,
                arrayminus=(total_df["kwh_twh"] - total_df["kwh_p10_twh"]).tolist()
                    if "kwh_p10_twh" in total_df.columns else None,
            ) if "kwh_p90_twh" in total_df.columns else None,
        ))
        fig_total.update_layout(
            title="Total ICT Electricity (TWh)",
            xaxis_title="Year",
            yaxis_title="TWh",
            showlegend=False,
        )
        st.plotly_chart(fig_total, use_container_width=True)

    with col2:
        if "emissions_mtco2e" in total_df.columns:
            fig_em = px.bar(
                total_df,
                x=total_df["year"].astype(str),
                y="emissions_mtco2e",
                color_discrete_sequence=[NEON_RED],
                labels={"emissions_mtco2e": "MtCO₂e", "x": "Year"},
                title="Total ICT Emissions (MtCO₂e)",
            )
            st.plotly_chart(fig_em, use_container_width=True)

    csv_total = total_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇ Download Table A (CSV)",
        data=csv_total,
        file_name=f"appendix_total_ict_{scenario}.csv",
        mime="text/csv",
    )
else:
    st.info("No total ICT data for selected filters.")

st.divider()

# ── Table 2: By application area ──────────────────────────────────────────────

st.subheader("Table B — Electricity by Application Area")

if not by_area_df.empty:
    display_area = by_area_df.copy()
    display_area["Application Area"] = display_area["application_area"].map(
        lambda a: AREA_LABELS.get(a, a)
    )
    for col in ["kwh_twh", "kwh_p10_twh", "kwh_p90_twh", "emissions_mtco2e"]:
        if col in display_area.columns:
            display_area[col] = display_area[col].round(3)

    st.dataframe(
        display_area.drop(columns=["application_area"]),
        use_container_width=True,
        hide_index=True,
    )

    fig_area = px.bar(
        by_area_df,
        x="year",
        y="kwh_twh",
        color="application_area",
        color_discrete_map=AREA_COLORS,
        barmode="stack",
        labels={"kwh_twh": "TWh", "year": "Year", "application_area": "Application Area"},
        title="ICT Electricity by Application Area at Reference Years",
    )
    fig_area.update_layout(legend_title="Application Area")
    st.plotly_chart(fig_area, use_container_width=True)

    csv_area = by_area_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇ Download Table B (CSV)",
        data=csv_area,
        file_name=f"appendix_by_area_{scenario}.csv",
        mime="text/csv",
    )
else:
    st.info("No application area data for selected filters.")

st.divider()

# ── Table 3: Per product group ────────────────────────────────────────────────

st.subheader("Table C — Per Product Group (Appendix Table)")

if not appendix_df.empty:
    display_pg = appendix_df.copy()
    display_pg["Application Area"] = display_pg["application_area"].map(
        lambda a: AREA_LABELS.get(a, a)
    )

    # Metric filter
    available_metrics = sorted(display_pg["metric"].unique())
    selected_metric = st.selectbox(
        "Metric",
        options=available_metrics,
        format_func=lambda m: {
            "kwh_twh": "Electricity (TWh)",
            "emissions_mtco2e": "Emissions (MtCO₂e)",
            "inventory_munits": "Inventory (M units)",
        }.get(m, m),
    )

    pg_display = display_pg[display_pg["metric"] == selected_metric].copy()
    year_cols = [str(y) for y in sorted(reference_years)]
    show_cols = ["Application Area", "product_group"] + [c for c in year_cols if c in pg_display.columns]

    for col in year_cols:
        if col in pg_display.columns:
            pg_display[col] = pg_display[col].round(4)

    st.dataframe(
        pg_display[show_cols].rename(columns={"product_group": "Product Group"}),
        use_container_width=True,
        hide_index=True,
    )

    # Heatmap of product group × year for selected metric
    if len(year_cols) >= 2:
        heat_data = pg_display.set_index("product_group")[
            [c for c in year_cols if c in pg_display.columns]
        ].fillna(0)

        fig_heat = px.imshow(
            heat_data,
            color_continuous_scale=[[0, CARD_BG], [0.4, MATRIX_GREEN], [1.0, CYAN]],
            labels={"x": "Year", "y": "Product Group", "color": selected_metric},
            title=f"Product Group Heatmap — {selected_metric}",
            aspect="auto",
        )
        fig_heat.update_xaxes(side="bottom")
        st.plotly_chart(fig_heat, use_container_width=True)

    csv_pg = appendix_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇ Download Table C — full appendix (CSV)",
        data=csv_pg,
        file_name=f"appendix_product_groups_{scenario}.csv",
        mime="text/csv",
    )
else:
    st.info("No product group data for selected filters.")

st.divider()

# ── Combined export ───────────────────────────────────────────────────────────

st.subheader("Combined Export")
st.markdown(
    f'<div style="color:{TEXT_DIM};font-size:0.85rem;margin-bottom:12px;">'
    "Download all three appendix tables as a single multi-sheet Excel workbook."
    "</div>",
    unsafe_allow_html=True,
)

if st.button("Build Excel workbook"):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        if not total_df.empty:
            total_df.to_excel(writer, sheet_name="A_Total_ICT", index=False)
        if not by_area_df.empty:
            by_area_df.to_excel(writer, sheet_name="B_By_Area", index=False)
        if not appendix_df.empty:
            appendix_df.to_excel(writer, sheet_name="C_Product_Groups", index=False)
    buf.seek(0)
    st.download_button(
        "⬇ Download Excel workbook",
        data=buf.getvalue(),
        file_name=f"ict_electricity_appendix_{scenario}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
