"""Scenarios page — compare electricity demand across named scenarios."""

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
    TEXT_DIM,
    TEXT_SECONDARY,
    apply_matrix_theme,
    matrix_card,
    matrix_header,
    _hex_to_rgb,
)

st.set_page_config(page_title="Scenarios — ICT Electricity", page_icon="🎛️", layout="wide")
apply_matrix_theme()

st.markdown(
    matrix_header(
        "🎛️ SCENARIO MATRIX",
        "Compare AI growth · sovereignty · grid constraint · efficiency scenarios",
    ),
    unsafe_allow_html=True,
)


@st.cache_data
def load_data() -> pd.DataFrame:
    """Load model output data."""
    return get_stub_dataframe()


df = load_data()

# ── Sidebar ───────────────────────────────────────────────────────────────────

st.sidebar.markdown("## ⚙ SCENARIO SETTINGS")

all_scenarios = sorted(df["scenario_id"].unique())
baseline = st.sidebar.selectbox(
    "Baseline scenario",
    all_scenarios,
    index=all_scenarios.index("ai_base") if "ai_base" in all_scenarios else 0,
)
compare = st.sidebar.multiselect(
    "Compare against",
    [s for s in all_scenarios if s != baseline],
    default=[s for s in all_scenarios if s != baseline],
)
selected_scenarios = [baseline] + compare

segments = st.sidebar.multiselect(
    "Segments", sorted(df["segment"].unique()), default=sorted(df["segment"].unique())
)
years = sorted(df["year"].unique())
year_range = st.sidebar.select_slider("Year range", options=years, value=(min(years), max(years)))

filtered = df[
    (df["scenario_id"].isin(selected_scenarios))
    & (df["segment"].isin(segments))
    & (df["year"] >= year_range[0])
    & (df["year"] <= year_range[1])
]

# ── Scenario comparison time series ──────────────────────────────────────────

st.subheader("Total ICT Electricity by Scenario")

ts = filtered.groupby(["year", "scenario_id"])["kwh_estimate"].sum().reset_index()
ts["TWh"] = ts["kwh_estimate"] / 1e9

fig = px.line(
    ts,
    x="year",
    y="TWh",
    color="scenario_id",
    color_discrete_map=SCENARIO_COLORS,
    markers=True,
    labels={"TWh": "Electricity (TWh)", "year": "Year", "scenario_id": "Scenario"},
    title="Total ICT Electricity Demand — Scenario Comparison",
)
fig.update_traces(line_width=2.5, marker_size=7)
fig.update_layout(hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

# ── Delta vs baseline ─────────────────────────────────────────────────────────

st.subheader(f"Delta vs Baseline — {baseline.replace('_', ' ').upper()}")

baseline_ts = ts[ts["scenario_id"] == baseline][["year", "TWh"]].rename(
    columns={"TWh": "baseline_twh"}
)
delta_df = ts[ts["scenario_id"] != baseline].merge(baseline_ts, on="year")
delta_df["delta_twh"] = delta_df["TWh"] - delta_df["baseline_twh"]
delta_df["delta_pct"] = delta_df["delta_twh"] / delta_df["baseline_twh"] * 100

if not delta_df.empty:
    fig2 = px.bar(
        delta_df,
        x="year",
        y="delta_pct",
        color="scenario_id",
        color_discrete_map=SCENARIO_COLORS,
        barmode="group",
        labels={"delta_pct": "Delta vs Baseline (%)", "year": "Year", "scenario_id": "Scenario"},
        title=f"Scenario Delta vs {baseline.replace('_', ' ').upper()} (%)",
    )
    fig2.add_hline(
        y=0,
        line_dash="dash",
        line_color="rgba(0,255,65,0.4)",
        annotation_text="Baseline",
        annotation_font_color=MATRIX_GREEN,
    )
    st.plotly_chart(fig2, use_container_width=True)

# ── DC segment focus ──────────────────────────────────────────────────────────

st.subheader("Data Centre Electricity by Scenario — P10/P50/P90")

dc = filtered[filtered["segment"] == "datacentres"]
if not dc.empty:
    dc_ts = dc.groupby(["year", "scenario_id"]).agg(
        kwh_p10=("kwh_p10", "sum"),
        kwh_p50=("kwh_p50", "sum"),
        kwh_p90=("kwh_p90", "sum"),
    ).reset_index()

    fig3 = go.Figure()
    for sid in selected_scenarios:
        sub = dc_ts[dc_ts["scenario_id"] == sid]
        color = SCENARIO_COLORS.get(sid, CYAN)
        rgb = _hex_to_rgb(color)
        fig3.add_trace(
            go.Scatter(
                x=sub["year"],
                y=sub["kwh_p90"] / 1e9,
                mode="lines",
                line=dict(color=f"rgba({rgb},0.3)", dash="dot", width=1),
                name=f"{sid} P90",
                showlegend=False,
            )
        )
        fig3.add_trace(
            go.Scatter(
                x=sub["year"],
                y=sub["kwh_p10"] / 1e9,
                mode="lines",
                line=dict(color=f"rgba({rgb},0.3)", dash="dot", width=1),
                fill="tonexty",
                fillcolor=f"rgba({rgb},0.07)",
                name=f"{sid} band",
                showlegend=True,
            )
        )
        fig3.add_trace(
            go.Scatter(
                x=sub["year"],
                y=sub["kwh_p50"] / 1e9,
                mode="lines",
                line=dict(color=color, width=2.5),
                name=f"{sid} P50",
            )
        )

    fig3.update_layout(
        xaxis_title="Year",
        yaxis_title="TWh",
        title="Data Centre Electricity — P50 with P10/P90 Uncertainty by Scenario",
        hovermode="x unified",
    )
    st.plotly_chart(fig3, use_container_width=True)

# ── Scenario cards ────────────────────────────────────────────────────────────

st.subheader("Scenario Definitions")

_SCENARIO_META = {
    "ai_base": (
        MATRIX_GREEN,
        "AI BASE",
        "Central AI compute growth trajectory. Hyperscale expansion continues at historical rates. "
        "PUE improves gradually (~2%/yr). AI workloads reach 30% of DC electricity by 2035.",
    ),
    "ai_low": (
        CYAN,
        "AI LOW",
        "Conservative AI adoption. Efficiency gains outpace demand growth. "
        "DC electricity demand grows slowly. Algorithmic efficiency breakthroughs materialise early.",
    ),
    "ai_high": (
        NEON_RED,
        "AI HIGH",
        "Accelerated AI build-out. Hyperscale capacity doubles by 2030. "
        "PUE improvements lag demand. AI workloads reach 50%+ of DC electricity by 2035.",
    ),
    "ai_stress": (
        "#FF6D00",
        "AI STRESS",
        "Extreme AI demand surge. Minimal efficiency gains. Grid pressure forces rationing. "
        "Stress-test ceiling for infrastructure planning.",
    ),
    "sovereignty_push": (
        AMBER,
        "SOVEREIGNTY PUSH",
        "Workload repatriation to national/regional clouds. Higher PUE on-prem infrastructure. "
        "Distributed DC footprint. Geopolitical fragmentation of hyperscale.",
    ),
    "grid_constrained": (
        "#AA00FF",
        "GRID CONSTRAINED",
        "Grid connection bottlenecks limit DC expansion. Lower utilisation rates. "
        "Slower AI growth due to power availability constraints.",
    ),
    "efficiency_breakthrough": (
        "#00BFA5",
        "EFFICIENCY BREAKTHROUGH",
        "Rapid PUE improvement and significant compute efficiency gains. "
        "Demand growth decouples from AI compute growth. Aggressive decarbonisation.",
    ),
}

cols = st.columns(2)
for i, sid in enumerate(selected_scenarios):
    color, label, desc = _SCENARIO_META.get(sid, (CYAN, sid.upper(), "No description available."))
    rgb = _hex_to_rgb(color)
    card_html = f"""
    <div style="
        background:{CARD_BG};
        border:1px solid rgba({rgb},0.30);
        border-left:4px solid {color};
        border-radius:6px;
        padding:16px 20px;
        margin-bottom:12px;
        box-shadow:0 0 18px rgba({rgb},0.08);
    ">
        <div style="color:{color};font-size:0.8rem;font-weight:700;letter-spacing:0.1em;margin-bottom:6px;">
            {'★ BASELINE — ' if sid == baseline else ''}{label}
        </div>
        <div style="color:{TEXT_SECONDARY};font-size:0.88rem;line-height:1.55;">{desc}</div>
    </div>
    """
    with cols[i % 2]:
        st.markdown(card_html, unsafe_allow_html=True)
