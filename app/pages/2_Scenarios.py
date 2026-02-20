"""Scenarios page — compare electricity demand across named scenarios."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.stub_data import get_stub_dataframe

st.set_page_config(page_title="Scenarios — ICT Electricity", page_icon="🎛️", layout="wide")
st.title("🎛️ Scenario Manager")
st.markdown(
    "Compare ICT electricity demand across AI growth, sovereignty, and grid scenarios. "
    "All scenarios share the same base data — differences reflect parameter assumptions only."
)


@st.cache_data
def load_data() -> pd.DataFrame:
    """Load model output data."""
    return get_stub_dataframe()


df = load_data()

# ── Sidebar ───────────────────────────────────────────────────────────────────

st.sidebar.header("Scenario Settings")

all_scenarios = sorted(df["scenario_id"].unique())
baseline = st.sidebar.selectbox("Baseline scenario", all_scenarios, index=all_scenarios.index("ai_base") if "ai_base" in all_scenarios else 0)
compare = st.sidebar.multiselect(
    "Compare against",
    [s for s in all_scenarios if s != baseline],
    default=[s for s in all_scenarios if s != baseline],
)
selected_scenarios = [baseline] + compare

segments = st.sidebar.multiselect("Segments", sorted(df["segment"].unique()), default=sorted(df["segment"].unique()))
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
    ts, x="year", y="TWh", color="scenario_id",
    markers=True,
    labels={"TWh": "Electricity (TWh)", "year": "Year", "scenario_id": "Scenario"},
    title="Total ICT Electricity Demand — Scenario Comparison",
)
fig.update_layout(hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

# ── Delta vs baseline ─────────────────────────────────────────────────────────

st.subheader(f"Delta vs Baseline ({baseline})")

baseline_ts = ts[ts["scenario_id"] == baseline][["year", "TWh"]].rename(columns={"TWh": "baseline_twh"})
delta_df = ts[ts["scenario_id"] != baseline].merge(baseline_ts, on="year")
delta_df["delta_twh"] = delta_df["TWh"] - delta_df["baseline_twh"]
delta_df["delta_pct"] = delta_df["delta_twh"] / delta_df["baseline_twh"] * 100

fig2 = px.bar(
    delta_df, x="year", y="delta_pct", color="scenario_id",
    barmode="group",
    labels={"delta_pct": "Delta vs Baseline (%)", "year": "Year", "scenario_id": "Scenario"},
    title=f"Scenario Delta vs {baseline} (%)",
)
fig2.add_hline(y=0, line_dash="dash", line_color="gray")
st.plotly_chart(fig2, use_container_width=True)

# ── DC segment focus ──────────────────────────────────────────────────────────

st.subheader("Data Centre Electricity by Scenario (with Uncertainty)")

dc = filtered[filtered["segment"] == "datacentres"]
if not dc.empty:
    dc_ts = dc.groupby(["year", "scenario_id"]).agg(
        kwh_p10=("kwh_p10", "sum"),
        kwh_p50=("kwh_p50", "sum"),
        kwh_p90=("kwh_p90", "sum"),
    ).reset_index()

    fig3 = go.Figure()
    colors = px.colors.qualitative.Set2
    for i, sid in enumerate(selected_scenarios):
        sub = dc_ts[dc_ts["scenario_id"] == sid]
        color = colors[i % len(colors)]
        fig3.add_trace(go.Scatter(
            x=sub["year"], y=sub["kwh_p90"] / 1e9,
            mode="lines", line=dict(color=color, dash="dot", width=1),
            name=f"{sid} P90", showlegend=False,
        ))
        fig3.add_trace(go.Scatter(
            x=sub["year"], y=sub["kwh_p10"] / 1e9,
            mode="lines", line=dict(color=color, dash="dot", width=1),
            fill="tonexty", fillcolor=color.replace("rgb", "rgba").replace(")", ",0.1)") if "rgb" in color else color,
            name=f"{sid} P10–P90", showlegend=True,
        ))
        fig3.add_trace(go.Scatter(
            x=sub["year"], y=sub["kwh_p50"] / 1e9,
            mode="lines", line=dict(color=color, width=2),
            name=f"{sid} P50",
        ))

    fig3.update_layout(
        xaxis_title="Year", yaxis_title="TWh",
        title="Data Centre Electricity — P50 with P10/P90 Bands by Scenario",
        hovermode="x unified",
    )
    st.plotly_chart(fig3, use_container_width=True)

# ── Scenario parameter summary ────────────────────────────────────────────────

st.subheader("Scenario Descriptions")

scenario_descriptions = {
    "ai_base": "**AI Base** — Central AI compute growth trajectory. Hyperscale expansion continues at historical rates. PUE improves gradually.",
    "ai_low": "**AI Low** — Conservative AI adoption. Efficiency gains outpace demand growth. DC electricity demand grows slowly.",
    "ai_high": "**AI High** — Accelerated AI build-out. Hyperscale capacity doubles by 2030. PUE improvements lag demand.",
    "sovereignty_push": "**Sovereignty Push** — Workload repatriation to national/regional clouds. Higher PUE on-prem infrastructure. Distributed DC footprint.",
}

for sid in selected_scenarios:
    desc = scenario_descriptions.get(sid, f"**{sid}** — No description available.")
    st.markdown(f"- {desc}")
