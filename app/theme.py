"""Shared Matrix-themed design system for the ICT Electricity Demand Streamlit app.

Provides colour constants, a custom Plotly template, CSS injection, and
HTML helper functions used across all pages.
"""

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# ── Colour palette ────────────────────────────────────────────────────────────

MATRIX_GREEN = "#00FF41"
MATRIX_GREEN_DIM = "#00CC33"
MATRIX_GREEN_GLOW = "rgba(0,255,65,0.15)"
CYAN = "#00E5FF"
CYAN_DIM = "#00B8D4"
CYAN_GLOW = "rgba(0,229,255,0.12)"
AMBER = "#FFB300"
AMBER_GLOW = "rgba(255,179,0,0.15)"
NEON_RED = "#FF1744"
NEON_RED_DIM = "#D50000"
NEON_RED_GLOW = "rgba(255,23,68,0.15)"
BG_DARK = "#0D0D0D"
CARD_BG = "#1A1A2E"
CARD_BORDER = "rgba(0,255,65,0.20)"
TEXT_PRIMARY = "#FFFFFF"
TEXT_SECONDARY = "#E0E0E0"
TEXT_DIM = "#8899AA"
GRID_LINE = "rgba(0,255,65,0.08)"

# Segment → colour mapping
SEGMENT_COLORS = {
    "datacentres": NEON_RED,
    "networks": CYAN,
    "devices": MATRIX_GREEN,
}

# Confidence tier → colour mapping
TIER_COLORS = {
    1: MATRIX_GREEN,
    2: AMBER,
    3: NEON_RED,
}

# Scenario → colour mapping
SCENARIO_COLORS = {
    "ai_base": MATRIX_GREEN,
    "ai_low": CYAN,
    "ai_high": NEON_RED,
    "ai_stress": "#FF6D00",
    "sovereignty_push": AMBER,
    "grid_constrained": "#AA00FF",
    "efficiency_breakthrough": "#00BFA5",
}

# ── Plotly template ───────────────────────────────────────────────────────────

_MATRIX_TEMPLATE = go.layout.Template(
    layout=go.Layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(13,13,13,0.6)",
        font=dict(family="'JetBrains Mono', 'Courier New', monospace", color=TEXT_SECONDARY, size=12),
        title=dict(font=dict(color=MATRIX_GREEN, size=16, family="'JetBrains Mono', monospace")),
        xaxis=dict(
            gridcolor=GRID_LINE,
            linecolor="rgba(0,255,65,0.3)",
            tickcolor="rgba(0,255,65,0.3)",
            tickfont=dict(color=TEXT_DIM),
            zerolinecolor="rgba(0,255,65,0.2)",
        ),
        yaxis=dict(
            gridcolor=GRID_LINE,
            linecolor="rgba(0,255,65,0.3)",
            tickcolor="rgba(0,255,65,0.3)",
            tickfont=dict(color=TEXT_DIM),
            zerolinecolor="rgba(0,255,65,0.2)",
        ),
        legend=dict(
            bgcolor="rgba(26,26,46,0.8)",
            bordercolor="rgba(0,255,65,0.3)",
            borderwidth=1,
            font=dict(color=TEXT_SECONDARY),
        ),
        colorway=[MATRIX_GREEN, CYAN, NEON_RED, AMBER, "#AA00FF", "#00BFA5", "#FF6D00"],
        hoverlabel=dict(
            bgcolor=CARD_BG,
            bordercolor=MATRIX_GREEN,
            font=dict(color=TEXT_PRIMARY, family="'JetBrains Mono', monospace"),
        ),
        margin=dict(l=40, r=20, t=50, b=40),
    )
)

pio.templates["matrix"] = _MATRIX_TEMPLATE
pio.templates.default = "matrix"

# ── CSS ───────────────────────────────────────────────────────────────────────

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;600;700&display=swap');

/* ── Root overrides ── */
html, body, [class*="css"] {
    font-family: 'JetBrains Mono', 'Courier New', monospace !important;
}

.stApp {
    background-color: #0D0D0D;
    background-image:
        linear-gradient(rgba(0,255,65,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,255,65,0.03) 1px, transparent 1px);
    background-size: 40px 40px;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background-color: #0A0A1A !important;
    border-right: 1px solid rgba(0,255,65,0.15) !important;
}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stMultiSelect label,
[data-testid="stSidebar"] .stSlider label,
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3, [data-testid="stSidebar"] p {
    color: #00FF41 !important;
    font-family: 'JetBrains Mono', monospace !important;
}

/* ── Headings ── */
h1 { color: #00FF41 !important; text-shadow: 0 0 20px rgba(0,255,65,0.5); }
h2 { color: #00E5FF !important; text-shadow: 0 0 12px rgba(0,229,255,0.3); }
h3 { color: #E0E0E0 !important; }

/* ── Divider ── */
hr {
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, transparent, #00FF41, transparent) !important;
    opacity: 0.4 !important;
    margin: 1.5rem 0 !important;
}

/* ── Metric cards ── */
[data-testid="stMetric"] {
    background: #1A1A2E;
    border: 1px solid rgba(0,255,65,0.20);
    border-left: 3px solid #00FF41;
    border-radius: 6px;
    padding: 16px 20px !important;
    box-shadow: 0 0 15px rgba(0,255,65,0.05), inset 0 0 30px rgba(0,0,0,0.3);
}
[data-testid="stMetricLabel"] {
    color: #8899AA !important;
    font-size: 0.75rem !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}
[data-testid="stMetricValue"] {
    color: #00FF41 !important;
    font-size: 1.8rem !important;
    font-weight: 700 !important;
    text-shadow: 0 0 10px rgba(0,255,65,0.4);
}
[data-testid="stMetricDelta"] { color: #00E5FF !important; }

/* ── Buttons ── */
.stDownloadButton > button, .stButton > button {
    background: transparent !important;
    color: #00FF41 !important;
    border: 1px solid #00FF41 !important;
    border-radius: 4px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.85rem !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 0 8px rgba(0,255,65,0.1) !important;
}
.stDownloadButton > button:hover, .stButton > button:hover {
    background: rgba(0,255,65,0.1) !important;
    box-shadow: 0 0 16px rgba(0,255,65,0.3) !important;
    transform: translateY(-1px) !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid rgba(0,255,65,0.2) !important;
    gap: 4px;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: #8899AA !important;
    border: none !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.85rem !important;
    padding: 8px 20px !important;
}
.stTabs [aria-selected="true"] {
    color: #00FF41 !important;
    border-bottom: 2px solid #00FF41 !important;
    text-shadow: 0 0 8px rgba(0,255,65,0.5) !important;
}

/* ── Selectbox / multiselect ── */
[data-baseweb="select"] {
    background-color: #1A1A2E !important;
    border-color: rgba(0,255,65,0.3) !important;
}
[data-baseweb="select"] * { color: #E0E0E0 !important; }

/* ── Expander ── */
[data-testid="stExpander"] {
    background: #1A1A2E !important;
    border: 1px solid rgba(0,255,65,0.15) !important;
    border-radius: 6px !important;
}
[data-testid="stExpander"] summary {
    color: #00E5FF !important;
    font-family: 'JetBrains Mono', monospace !important;
}

/* ── Info / warning / success boxes ── */
[data-testid="stAlert"] {
    background: #1A1A2E !important;
    border-radius: 6px !important;
    font-family: 'JetBrains Mono', monospace !important;
}

/* ── Dataframe ── */
[data-testid="stDataFrame"] {
    border: 1px solid rgba(0,255,65,0.15) !important;
    border-radius: 6px !important;
}

/* ── Caption / footer ── */
.stCaption, [data-testid="stCaptionContainer"] {
    color: #445566 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.75rem !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0D0D0D; }
::-webkit-scrollbar-thumb { background: rgba(0,255,65,0.3); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(0,255,65,0.6); }
</style>
"""

# ── Public API ─────────────────────────────────────────────────────────────────


def apply_matrix_theme() -> None:
    """Inject Matrix CSS and set Plotly default template.

    Call once at the top of each Streamlit page, after st.set_page_config.
    """
    st.markdown(_CSS, unsafe_allow_html=True)
    pio.templates.default = "matrix"


def matrix_kpi_card(label: str, value: str, sub: str = "", color: str = MATRIX_GREEN) -> str:
    """Return HTML for a styled KPI card.

    Args:
        label: Short uppercase label.
        value: Primary display value (large text).
        sub: Optional subtitle / delta line.
        color: Accent colour for border and value glow.

    Returns:
        HTML string suitable for st.markdown(unsafe_allow_html=True).
    """
    sub_html = f'<div style="color:{TEXT_DIM};font-size:0.75rem;margin-top:4px;">{sub}</div>' if sub else ""
    return f"""
    <div style="
        background:{CARD_BG};
        border:1px solid rgba({_hex_to_rgb(color)},0.25);
        border-left:3px solid {color};
        border-radius:6px;
        padding:18px 22px;
        box-shadow:0 0 20px rgba({_hex_to_rgb(color)},0.06);
    ">
        <div style="color:{TEXT_DIM};font-size:0.7rem;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:6px;">{label}</div>
        <div style="color:{color};font-size:1.9rem;font-weight:700;text-shadow:0 0 12px rgba({_hex_to_rgb(color)},0.4);line-height:1.1;">{value}</div>
        {sub_html}
    </div>
    """


def matrix_card(title: str, body: str, color: str = CYAN) -> str:
    """Return HTML for a generic glowing panel card.

    Args:
        title: Card heading.
        body: HTML body content.
        color: Accent colour for border glow.

    Returns:
        HTML string suitable for st.markdown(unsafe_allow_html=True).
    """
    return f"""
    <div style="
        background:{CARD_BG};
        border:1px solid rgba({_hex_to_rgb(color)},0.25);
        border-radius:6px;
        padding:16px 20px;
        margin-bottom:12px;
        box-shadow:0 0 16px rgba({_hex_to_rgb(color)},0.05);
    ">
        <div style="color:{color};font-size:0.85rem;font-weight:600;margin-bottom:8px;text-transform:uppercase;letter-spacing:0.06em;">{title}</div>
        <div style="color:{TEXT_SECONDARY};font-size:0.9rem;line-height:1.5;">{body}</div>
    </div>
    """


def matrix_header(title: str, subtitle: str = "") -> str:
    """Return HTML for a glowing page header.

    Args:
        title: Main title text.
        subtitle: Optional subtitle line.

    Returns:
        HTML string.
    """
    sub_html = (
        f'<p style="color:{TEXT_DIM};font-size:0.9rem;margin-top:6px;font-weight:300;">{subtitle}</p>'
        if subtitle
        else ""
    )
    return f"""
    <div style="margin-bottom:24px;">
        <h1 style="
            color:{MATRIX_GREEN};
            font-family:\'JetBrains Mono\',monospace;
            font-size:2rem;
            font-weight:700;
            text-shadow:0 0 24px rgba(0,255,65,0.5);
            margin:0;
            letter-spacing:0.04em;
        ">{title}</h1>
        {sub_html}
    </div>
    """


def tier_badge(tier: int) -> str:
    """Return a small inline HTML badge for a confidence tier.

    Args:
        tier: 1, 2, or 3.

    Returns:
        HTML string.
    """
    color = TIER_COLORS.get(tier, TEXT_DIM)
    labels = {1: "T1 HIGH", 2: "T2 MED", 3: "T3 LOW"}
    label = labels.get(tier, f"T{tier}")
    return (
        f'<span style="background:rgba({_hex_to_rgb(color)},0.15);color:{color};'
        f'border:1px solid rgba({_hex_to_rgb(color)},0.4);border-radius:3px;'
        f'padding:2px 7px;font-size:0.7rem;font-weight:600;letter-spacing:0.08em;">{label}</span>'
    )


def _hex_to_rgb(hex_color: str) -> str:
    """Convert a hex colour string to comma-separated RGB values.

    Args:
        hex_color: Hex string like '#00FF41'.

    Returns:
        String like '0,255,65'.
    """
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"{r},{g},{b}"
