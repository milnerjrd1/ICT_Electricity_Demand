"""Confidence page — colour-coded confidence tiers with drill-down to data quality."""

import pandas as pd
import plotly.express as px
import streamlit as st

from app.stub_data import get_stub_dataframe

st.set_page_config(page_title="Confidence — ICT Electricity", page_icon="🎯", layout="wide")
st.title("🎯 Confidence Lens")
st.markdown(
    "Every output cell carries a **confidence tier** (1–3) driven by source quality, "
    "coverage, triangulation, and sensitivity. Use this page to understand where to trust "
    "the numbers and where uncertainty is wide."
)

TIER_LABELS = {1: "Tier 1 — High", 2: "Tier 2 — Medium", 3: "Tier 3 — Low"}
TIER_COLORS = {1: "#10B981", 2: "#F59E0B", 3: "#EF4444"}
TIER_DESCRIPTIONS = {
    1: "Official statistics / regulator data. >80% segment coverage. 3+ independent sources agree within 15%.",
    2: "Industry reports / surveys. 40–80% coverage. 2 sources agree within 25%.",
    3: "Estimates / proxies. <40% coverage or single source. High sensitivity to assumptions.",
}


@st.cache_data
def load_data() -> pd.DataFrame:
    """Load model output data."""
    return get_stub_dataframe()


df = load_data()

# ── Sidebar ───────────────────────────────────────────────────────────────────

st.sidebar.header("Filters")
scenario = st.sidebar.selectbox("Scenario", sorted(df["scenario_id"].unique()))
year = st.sidebar.selectbox("Year", sorted(df["year"].unique(), reverse=True))

filtered = df[(df["scenario_id"] == scenario) & (df["year"] == year)]

# ── Tier legend ───────────────────────────────────────────────────────────────

col1, col2, col3 = st.columns(3)
for col, (tier, label) in zip([col1, col2, col3], TIER_LABELS.items()):
    with col:
        n_rows = len(filtered[filtered["confidence_tier"] == tier])
        twh = filtered[filtered["confidence_tier"] == tier]["kwh_estimate"].sum() / 1e9
        st.markdown(
            f"""
            <div style="background:{TIER_COLORS[tier]}22; border-left:4px solid {TIER_COLORS[tier]};
                        padding:12px; border-radius:4px;">
            <b style="color:{TIER_COLORS[tier]}">{label}</b><br>
            {n_rows:,} output cells · {twh:,.0f} TWh<br>
            <small>{TIER_DESCRIPTIONS[tier]}</small>
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
        color_continuous_scale=[[0, "#10B981"], [0.5, "#F59E0B"], [1.0, "#EF4444"]],
        zmin=1, zmax=3,
        labels={"color": "Avg Confidence Tier"},
        title=f"Average Confidence Tier by Geography × Segment ({year})",
        aspect="auto",
    )
    fig.update_coloraxes(colorbar_tickvals=[1, 2, 3], colorbar_ticktext=["1 High", "2 Med", "3 Low"])
    st.plotly_chart(fig, use_container_width=True)

# ── Uncertainty band distribution ─────────────────────────────────────────────

st.subheader("Uncertainty Band Distribution by Segment")

fig2 = px.box(
    filtered,
    x="segment",
    y="uncertainty_band",
    color="segment",
    color_discrete_map={"datacentres": "#EF4444", "networks": "#3B82F6", "devices": "#10B981"},
    labels={"uncertainty_band": "Uncertainty Band (fractional ±)", "segment": "Segment"},
    title="Uncertainty Band Distribution (fractional half-width)",
)
fig2.update_layout(showlegend=False)
st.plotly_chart(fig2, use_container_width=True)

# ── Confidence by geography bar ───────────────────────────────────────────────

st.subheader("Average Confidence Tier by Geography")

geo_conf = (
    filtered.groupby("geo")["confidence_tier"]
    .mean()
    .reset_index()
    .sort_values("confidence_tier")
)
geo_conf["color"] = geo_conf["confidence_tier"].apply(
    lambda t: "#10B981" if t < 1.5 else ("#F59E0B" if t < 2.5 else "#EF4444")
)

fig3 = px.bar(
    geo_conf,
    x="geo",
    y="confidence_tier",
    color="confidence_tier",
    color_continuous_scale=[[0, "#10B981"], [0.5, "#F59E0B"], [1.0, "#EF4444"]],
    zmin=1, zmax=3,
    labels={"confidence_tier": "Avg Confidence Tier", "geo": "Geography"},
    title="Average Confidence Tier by Geography",
)
fig3.update_coloraxes(showscale=False)
fig3.add_hline(y=2, line_dash="dash", line_color="gray", annotation_text="Tier 2 threshold")
st.plotly_chart(fig3, use_container_width=True)

# ── Tier definitions ──────────────────────────────────────────────────────────

with st.expander("Confidence tier methodology"):
    st.markdown(
        """
        | Factor | Tier 1 (High) | Tier 2 (Medium) | Tier 3 (Low) |
        |---|---|---|---|
        | Source quality | Official stats / regulator data | Industry reports / surveys | Estimates / expert judgment |
        | Coverage | >80% of segment covered | 40–80% covered | <40% or pure proxy |
        | Triangulation | 3+ sources agree within 15% | 2 sources agree within 25% | Single source or >25% divergence |
        | Sensitivity | Output stable (±10%) | Moderate sensitivity (±10–30%) | High sensitivity (>30% swing) |
        | Uncertainty band | ±10% | ±20% | ±35% |
        """
    )
