"""
Tiger Analytics — Starter Streamlit App Template
==================================================

A minimal, production-ready Streamlit in Snowflake app with:
- Tiger Analytics branding (header, footer, accent colors)
- Dark / Light / System theme support via pure Python CSS injection
- Auto theme detection via st.get_option (no manual toggle needed)
- Branded KPI cards, Plotly chart, and data table
- Multi-strategy Snowflake session establishment
- Cached query helpers

Usage:
  1. Copy this file to your app directory as `streamlit_app.py`
  2. Copy `assets/` directory into your app root
  3. Replace placeholder logos in `assets/logos/` with official brand assets
  4. (Optional) Copy `templates/config.toml` to `.streamlit/config.toml`
  5. Deploy to Snowflake via Snowsight or Cortex Code CLI

Author:  Tiger Analytics Engineering
Version: 3.0.0
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ─────────────────────────────────────────────────────────────────────────────
# 1. Page Config (must be the first Streamlit command)
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Tiger Analytics | Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Brand Tokens
# ─────────────────────────────────────────────────────────────────────────────
TA_ORANGE        = "#F15A22"
TA_ORANGE_DARK   = "#D94E1C"
TA_NAVY          = "#1A1A2E"
TA_GREY_100      = "#F5F5F5"
TA_GREY_200      = "#E0E0E0"
TA_GREY_700      = "#4A4A68"
TA_TEXT_LIGHT    = "#1A1A2E"
TA_TEXT_DARK     = "#E6EDF3"
TA_DARK_BG       = "#0D1117"
TA_DARK_SURFACE  = "#161B22"
TA_DARK_BORDER   = "#2D333B"
TA_DARK_TEXT_MUTED = "#8B949E"

CHART_COLORS = [
    "#F15A22", "#2196F3", "#4CAF50", "#FF9800",
    "#9C27B0", "#00BCD4", "#E91E63", "#8BC34A",
]


# ─────────────────────────────────────────────────────────────────────────────
# 3. Theme Detection (auto — Snowsight propagates theme to Streamlit iframe)
# ─────────────────────────────────────────────────────────────────────────────
def _is_dark_color(hex_color: str) -> bool:
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return False
    r, g, b = int(h[:2], 16), int(h[2:4], 16), int(h[4:], 16)
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255 < 0.5


def get_active_theme() -> str:
    """Auto-detect Snowsight theme. No manual toggle needed."""
    try:
        bg = st.get_option("theme.backgroundColor")
        if bg and _is_dark_color(bg):
            return "dark"
        if bg:
            return "light"
    except Exception:
        pass
    return "light"


THEME = get_active_theme()
IS_DARK = THEME == "dark"


# ─────────────────────────────────────────────────────────────────────────────
# 4. CSS Injection — PRIMARY THEMING MECHANISM
# ─────────────────────────────────────────────────────────────────────────────
_accent   = TA_ORANGE
_bg       = TA_DARK_BG if IS_DARK else "#FFFFFF"
_bg2      = TA_DARK_SURFACE if IS_DARK else TA_GREY_100
_text     = TA_TEXT_DARK if IS_DARK else TA_TEXT_LIGHT
_text_m   = TA_DARK_TEXT_MUTED if IS_DARK else TA_GREY_700
_border   = TA_DARK_BORDER if IS_DARK else TA_GREY_200
_card_bg  = TA_DARK_SURFACE if IS_DARK else TA_GREY_100
_sb_bg    = "#010409" if IS_DARK else TA_NAVY
_sb_text  = TA_TEXT_DARK if IS_DARK else "#FFFFFF"

st.markdown(f"""
<style>
    /* ═══ PAGE-LEVEL ═══ */
    .stApp {{
        background-color: {_bg};
        color: {_text};
        font-family: 'Source Sans Pro', 'Segoe UI', sans-serif;
    }}
    [data-testid="stAppViewContainer"] {{
        background-color: {_bg};
        color: {_text};
    }}
    h1, h2, h3, h4, h5, h6 {{
        color: {_text};
    }}
    .stMarkdown, .stText, .stCaption {{
        color: {_text};
    }}

    /* ═══ SIDEBAR ═══ */
    section[data-testid="stSidebar"] {{
        background-color: {_sb_bg};
        color: {_sb_text};
    }}
    section[data-testid="stSidebar"] > div:first-child {{
        border-top: 4px solid {_accent};
    }}
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] .stRadio label,
    section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label,
    section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label p,
    section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label div,
    section[data-testid="stSidebar"] .stSelectbox label {{
        color: {_sb_text} !important;
    }}

    /* ═══ METRIC CARDS ═══ */
    div[data-testid="stMetric"] {{
        background-color: {_card_bg};
        border-left: 4px solid {_accent};
        border-radius: 8px;
        padding: 12px 16px;
    }}

    /* ═══ BUTTONS ═══ */
    .stButton > button {{
        background-color: {_accent};
        color: #FFFFFF;
        border: none;
        border-radius: 6px;
        font-weight: 600;
    }}
    .stButton > button:hover {{
        background-color: {TA_ORANGE_DARK};
        color: #FFFFFF;
    }}

    /* ═══ DOWNLOAD BUTTON ═══ */
    .stDownloadButton > button {{
        background-color: {_accent};
        color: #FFFFFF !important;
        border: none;
        border-radius: 6px;
        font-weight: 600;
    }}
    .stDownloadButton > button:hover {{
        background-color: {TA_ORANGE_DARK};
        color: #FFFFFF !important;
    }}

    /* ═══ TABS ═══ */
    .stTabs [aria-selected="true"] {{
        border-bottom-color: {_accent} !important;
        color: {_accent} !important;
    }}

    /* ═══ LINKS ═══ */
    a {{ color: {_accent}; }}

    /* ═══ INPUTS ═══ */
    .stSelectbox > div > div,
    .stMultiSelect > div > div,
    .stTextInput > div > div {{
        border-color: {_border};
    }}

    /* ═══ SPACING ═══ */
    div.block-container {{
        padding-top: 1.5rem;
    }}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Snowflake Session Establishment (multi-strategy fallback)
# ─────────────────────────────────────────────────────────────────────────────
IN_SIS = False
session = None

try:
    from snowflake.snowpark.context import get_active_session
    session = get_active_session()
    IN_SIS = True
except Exception:
    pass

if session is None:
    try:
        conn = st.connection("snowflake")
        session = conn.session()
        IN_SIS = True
    except Exception:
        pass

if session is None:
    try:
        from snowflake.snowpark import Session
        session = Session.builder.config("connection_name", "default").create()
    except Exception:
        st.error("Could not establish Snowflake connection.")
        st.stop()


# ─────────────────────────────────────────────────────────────────────────────
# 6. Cached Query Helpers
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=900, show_spinner=False)
def run_query(_session, query: str) -> pd.DataFrame:
    """Standard cached query — 15 min TTL."""
    return _session.sql(query).to_pandas()


def sv(val, default=0):
    """Safe value extraction — guard against None from Snowflake aggregations."""
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


# ─────────────────────────────────────────────────────────────────────────────
# 7. Header
# ─────────────────────────────────────────────────────────────────────────────
def render_header(title: str):
    logo = "assets/logos/ta_logo_dark.svg" if IS_DARK else "assets/logos/ta_logo_light.svg"
    text_color = TA_TEXT_DARK if IS_DARK else TA_TEXT_LIGHT
    col_logo, col_title = st.columns([1, 5])
    with col_logo:
        st.image(logo, width=120)
    with col_title:
        st.markdown(
            f'<h2 style="margin:0;padding:0;font-size:1.6rem;font-weight:700;color:{text_color};">{title}</h2>',
            unsafe_allow_html=True,
        )


render_header("Sample Dashboard")


# ─────────────────────────────────────────────────────────────────────────────
# 8. Sidebar — Branding + Navigation
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("assets/logos/ta_logo_dark.svg", width=140)
    st.markdown("---")

    st.markdown("**Navigation**")
    page = st.radio(
        "Go to",
        ["📊 Overview", "📈 Details", "⚙️ Settings"],
        label_visibility="collapsed",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 9. KPI Row
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("#### Key Metrics")
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.metric(label="Total Revenue", value="$12.4M", delta="+8.2%")
with kpi2:
    st.metric(label="Active Users", value="3,421", delta="+142")
with kpi3:
    st.metric(label="Forecast MAPE", value="4.7%", delta="-0.3%")
with kpi4:
    st.metric(label="Model Accuracy", value="94.2%", delta="+1.1%")


# ─────────────────────────────────────────────────────────────────────────────
# 10. Charts — theme-aware Plotly
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("#### Trend Analysis")

months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
revenue = [1.8, 2.1, 1.9, 2.4, 2.6, 2.8]
forecast = [1.7, 2.0, 2.0, 2.3, 2.5, 2.9]

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=months, y=revenue, mode="lines+markers",
    name="Actual", line=dict(color=CHART_COLORS[0], width=3),
))
fig.add_trace(go.Scatter(
    x=months, y=forecast, mode="lines",
    name="Forecast", line=dict(color=CHART_COLORS[1], width=2, dash="dash"),
))

fig.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Source Sans Pro, sans-serif", color=_text),
    xaxis=dict(gridcolor=_border, tickfont=dict(color=_text)),
    yaxis=dict(gridcolor=_border, title="Revenue ($M)", tickfont=dict(color=_text)),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=_text)),
    margin=dict(l=40, r=20, t=20, b=40),
    height=380,
)

col_chart, col_summary = st.columns([3, 1])
with col_chart:
    st.plotly_chart(fig, use_container_width=True)
with col_summary:
    st.markdown("**Summary**")
    st.markdown(f"Peak month: **Jun** (${revenue[-1]}M)")
    st.markdown(f"Avg growth: **+{((revenue[-1] - revenue[0]) / revenue[0] * 100):.1f}%**")
    st.markdown("Forecast accuracy: **97.3%**")


# ─────────────────────────────────────────────────────────────────────────────
# 11. Data Table
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("#### Detailed Data")

df = pd.DataFrame({
    "Month": months,
    "Revenue ($M)": revenue,
    "Forecast ($M)": forecast,
    "Variance (%)": [
        round((a - f) / f * 100, 1) for a, f in zip(revenue, forecast)
    ],
})

st.dataframe(df, use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────────────────────────────────────
# 12. Footer
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    f'<p style="text-align:center; color:{_text_m}; font-size:0.8rem;">'
    f'Powered by <span style="color:{TA_ORANGE}; font-weight:600;">Tiger Analytics</span>'
    f' · Built on Snowflake</p>',
    unsafe_allow_html=True,
)
