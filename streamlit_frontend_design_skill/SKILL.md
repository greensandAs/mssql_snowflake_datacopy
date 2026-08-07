---
name: ta-streamlit-design
description: >
  Tiger Analytics branded Streamlit frontend design skill for Snowflake.
  Use when building, styling, or customizing Streamlit in Snowflake (SiS) apps
  with Tiger Analytics brand identity. Handles dark/light/system theme support
  in Snowsight, branded components, layout patterns, chart theming, and
  custom CSS injection. Invoke for any Streamlit UI task — new apps, restyling
  existing apps, adding branded headers/footers, theming charts, or building
  dashboard layouts.
---

# Tiger Analytics — Streamlit in Snowflake Design Skill

This skill guides the creation of **production-grade, brand-compliant Streamlit apps** that run inside Snowflake Snowsight. Every app produced with this skill must look and feel like a first-party Tiger Analytics product — polished, accessible, and consistent across light, dark, and system-preferred appearance modes.

> **Important**: Before writing any code, read `references/BRAND_SYSTEM.md` for color tokens, typography, and logo usage rules. Read `references/SNOWSIGHT_THEMING.md` for the Snowsight-specific dark/light mode handling patterns.

---

## 1. Design Principles

1. **Brand First** — Every visual decision traces back to the Tiger Analytics brand system. No ad-hoc colors, no off-brand fonts.
2. **Theme-Adaptive** — All apps MUST render correctly in Snowsight Light mode, Dark mode, and System (auto) preference. Never hard-code background or text colors without a theme-aware fallback.
3. **Data-Forward** — Interfaces serve the data. Typography, spacing, and color choices optimize for readability of tables, charts, and KPIs.
4. **Accessible** — Maintain WCAG 2.1 AA contrast ratios across both themes. Use semantic hierarchy (`st.header`, `st.subheader`) for screen readers.
5. **Minimal Custom CSS** — Prefer Streamlit's native theming via `config.toml` and `st.set_page_config`. Use `st.markdown(unsafe_allow_html=True)` CSS only when native options are insufficient.
6. **Snowflake-Compatible** — Only use packages available in the Snowflake Anaconda channel. Validate `streamlit-extras` features against SiS compatibility.

---

## 2. Before You Code — Checklist

- [ ] Identify the app type: Dashboard, Data Explorer, Admin Tool, Form, Report
- [ ] Confirm the target audience: Internal analysts, executives, external clients
- [ ] Determine data sources: Snowflake tables, stages, Cortex ML outputs
- [ ] Check Snowsight version for Custom UI / `unsafe_allow_html` support
- [ ] Load brand tokens from `references/BRAND_SYSTEM.md`
- [ ] Review layout templates in `templates/`

---

## 3. Project Structure

Every Streamlit in Snowflake app built with this skill should follow this structure:

```
my_app/
├── .streamlit/
│   └── config.toml              # OPTIONAL — minimal safe subset only (see §4.1)
├── assets/
│   ├── logos/
│   │   ├── ta_logo_light.svg    # Logo for light backgrounds
│   │   ├── ta_logo_dark.svg     # Logo for dark backgrounds
│   │   └── ta_favicon.png       # 32x32 favicon
│   └── brand/
│       └── brand_tokens.py      # Python dict of brand colors/fonts
├── components/
│   ├── header.py                # Branded header with theme-aware logo
│   ├── footer.py                # Branded footer
│   ├── sidebar.py               # Sidebar with branding and navigation
│   ├── kpi_cards.py             # KPI metric cards
│   └── chart_theme.py           # Plotly/Altair theme factory
├── utils/
│   ├── theme_detect.py          # Runtime theme detection helper
│   └── css_injector.py          # Centralized CSS injection
├── pages/                       # Multi-page app pages
│   ├── 1_Overview.py
│   └── 2_Details.py
└── streamlit_app.py             # Main entry point
```

---

## 4. Theme Configuration

### 4.1 Why NOT config.toml

> **IMPORTANT**: `config.toml` has **limited and unreliable support** in Streamlit in Snowflake. Warehouse runtimes support only a small subset of config options, and advanced features like `[theme.light]` / `[theme.dark]` dual-theme blocks are **NOT supported** in SiS. Container runtimes have broader support but still not full parity with open-source Streamlit.

**Primary approach**: Do ALL theming via **pure Python CSS injection** using `st.markdown(unsafe_allow_html=True)`. This is the most reliable, portable, and testable approach across both warehouse and container runtimes in Snowflake.

**Optional fallback**: If your team is on container runtimes and has verified `[theme]` support, you may use a minimal `config.toml` for basic `primaryColor` only — but NEVER rely on it as the sole theming mechanism.

```toml
# .streamlit/config.toml — OPTIONAL, minimal safe subset only
# Only use this if verified working in your runtime. All visual theming
# should be handled via Python CSS injection regardless.
[theme]
primaryColor = "#F15A22"
```

### 4.2 Runtime Theme Detection

Snowsight switches between light and dark appearance. Your app needs to detect the active mode at runtime to adapt colors, logos, and chart palettes. Snowsight automatically propagates its theme to the embedded Streamlit app via `st.get_option("theme.backgroundColor")`. Use this for **fully automatic** detection — no manual toggle needed:

```python
# utils/theme_detect.py
import streamlit as st


def get_active_theme() -> str:
    """Detect whether Snowsight is rendering in light or dark mode.

    Reads the resolved backgroundColor that Snowsight propagates into the
    Streamlit iframe. Computes luminance to classify as light or dark.
    Falls back to 'light' (Snowsight's default) if detection fails.

    Returns 'light' or 'dark'.
    """
    try:
        bg = st.get_option("theme.backgroundColor")
        if bg and _is_dark_color(bg):
            return "dark"
        if bg:
            return "light"
    except Exception:
        pass
    return "light"


def _is_dark_color(hex_color: str) -> bool:
    """Simple luminance check on a hex color string."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return False
    r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:], 16)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return luminance < 0.5
```

> **How it works**: When a user switches Snowsight to Light, Dark, or System mode, Snowsight injects the resolved theme colors into the Streamlit iframe. `st.get_option("theme.backgroundColor")` reads this resolved value — so it automatically follows System (OS) preference too. No manual toggle is required.

### 4.3 Theme-Aware Logo Selection

```python
# components/header.py
import streamlit as st
from utils.theme_detect import get_active_theme

def render_header(title: str = "Tiger Analytics"):
    theme = get_active_theme()
    is_dark = theme == "dark"
    text_color = "#E6EDF3" if is_dark else "#1A1A2E"
    logo_path = (
        "assets/logos/ta_logo_dark.svg"
        if is_dark
        else "assets/logos/ta_logo_light.svg"
    )
    col_logo, col_title = st.columns([1, 5])
    with col_logo:
        st.image(logo_path, width=120)
    with col_title:
        st.markdown(
            f'<h2 style="margin:0;padding:0;font-size:1.6rem;font-weight:700;color:{text_color};">{title}</h2>',
            unsafe_allow_html=True,
        )
```

---

## 5. Brand-Compliant CSS Injection (Primary Theming Mechanism)

Since `config.toml` is unreliable in SiS, **CSS injection is the primary theming method**. It handles all backgrounds, text colors, sidebar styling, and component branding. Call `inject_global_css()` once at the top of your `streamlit_app.py`, immediately after `st.set_page_config()`.

**Never scatter `st.markdown` CSS blocks throughout the app.** All CSS lives in one function.

```python
# utils/css_injector.py
import streamlit as st
from utils.theme_detect import get_active_theme

# ---------- Tiger Analytics Brand Tokens ----------
TA_ORANGE       = "#F15A22"
TA_ORANGE_DARK  = "#D94E1C"
TA_NAVY         = "#1A1A2E"
TA_DARK_BG      = "#0D1117"
TA_LIGHT_BG     = "#FFFFFF"
TA_GREY_100     = "#F5F5F5"
TA_GREY_200     = "#E0E0E0"
TA_GREY_700     = "#4A4A68"
TA_TEXT_LIGHT    = "#1A1A2E"
TA_TEXT_DARK     = "#E6EDF3"
TA_DARK_SURFACE  = "#161B22"
TA_DARK_BORDER   = "#2D333B"
TA_DARK_TEXT_MUTED = "#8B949E"

def inject_global_css():
    """Inject Tiger Analytics global styles. Call once in streamlit_app.py.

    This is the PRIMARY theming mechanism for SiS apps. It replaces
    config.toml [theme] blocks which have limited support in Snowflake.
    Handles: page backgrounds, text colors, sidebar, metric cards,
    buttons, tabs, links, dataframes, and spacing.
    """
    theme = get_active_theme()
    is_dark = theme == "dark"

    accent   = TA_ORANGE
    bg       = TA_DARK_BG if is_dark else TA_LIGHT_BG
    bg2      = TA_DARK_SURFACE if is_dark else TA_GREY_100
    text     = TA_TEXT_DARK if is_dark else TA_TEXT_LIGHT
    text_m   = TA_DARK_TEXT_MUTED if is_dark else TA_GREY_700
    border   = TA_DARK_BORDER if is_dark else TA_GREY_200
    card_bg  = TA_DARK_SURFACE if is_dark else TA_GREY_100
    sb_bg    = "#010409" if is_dark else TA_NAVY
    sb_text  = TA_TEXT_DARK if is_dark else "#FFFFFF"

    st.markdown(f"""
    <style>
        /* ========== PAGE-LEVEL THEMING ========== */
        /* Main app background and text */
        .stApp {{
            background-color: {bg};
            color: {text};
            font-family: 'Source Sans Pro', 'Segoe UI', sans-serif;
        }}

        /* App view container (fallback for nested containers) */
        [data-testid="stAppViewContainer"] {{
            background-color: {bg};
            color: {text};
        }}

        /* Secondary background areas (expanders, secondary panels) */
        [data-testid="stExpander"],
        .stCodeBlock {{
            background-color: {bg2};
        }}

        /* ========== SIDEBAR THEMING ========== */
        section[data-testid="stSidebar"] {{
            background-color: {sb_bg};
            color: {sb_text};
        }}
        section[data-testid="stSidebar"] > div:first-child {{
            border-top: 4px solid {accent};
        }}
        section[data-testid="stSidebar"] .stMarkdown,
        section[data-testid="stSidebar"] .stRadio label,
        section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label,
        section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label p,
        section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label div,
        section[data-testid="stSidebar"] .stSelectbox label {{
            color: {sb_text} !important;
        }}

        /* ========== COMPONENT THEMING ========== */

        /* Branded metric cards */
        div[data-testid="stMetric"] {{
            background-color: {card_bg};
            border-left: 4px solid {accent};
            border-radius: 8px;
            padding: 12px 16px;
        }}

        /* Branded buttons */
        .stButton > button {{
            background-color: {accent};
            color: #FFFFFF;
            border: none;
            border-radius: 6px;
            font-weight: 600;
        }}
        .stButton > button:hover {{
            background-color: {TA_ORANGE_DARK};
            color: #FFFFFF;
        }}

        /* Tab underline accent */
        .stTabs [aria-selected="true"] {{
            border-bottom-color: {accent} !important;
            color: {accent} !important;
        }}

        /* Links */
        a {{
            color: {accent};
        }}

        /* Dataframe / table headers */
        .stDataFrame th {{
            background-color: {bg2};
            color: {text};
        }}

        /* Selectbox, multiselect, text_input borders */
        .stSelectbox > div > div,
        .stMultiSelect > div > div,
        .stTextInput > div > div {{
            border-color: {border};
        }}

        /* ========== SPACING ========== */
        /* Reduce default top padding */
        div.block-container {{
            padding-top: 1.5rem;
        }}

        /* ========== DOWNLOAD BUTTON ========== */
        .stDownloadButton > button {{
            background-color: {accent};
            color: #FFFFFF !important;
            border: none;
            border-radius: 6px;
            font-weight: 600;
        }}
        .stDownloadButton > button:hover {{
            background-color: {TA_ORANGE_DARK};
            color: #FFFFFF !important;
        }}

        /* ========== MARKDOWN TEXT ========== */
        .stMarkdown, .stText, .stCaption {{
            color: {text};
        }}
        h1, h2, h3, h4, h5, h6 {{
            color: {text};
        }}
    </style>
    """, unsafe_allow_html=True)
```

---

## 6. Component Patterns

### 6.1 KPI Metric Cards

```python
# components/kpi_cards.py
import streamlit as st

def render_kpi_row(metrics: list[dict]):
    """Render a row of branded KPI cards.

    Args:
        metrics: List of dicts with keys 'label', 'value', 'delta' (optional).
    """
    cols = st.columns(len(metrics))
    for col, m in zip(cols, metrics):
        with col:
            st.metric(
                label=m["label"],
                value=m["value"],
                delta=m.get("delta"),
            )
```

### 6.2 Chart Theming — Plotly

```python
# components/chart_theme.py
from utils.theme_detect import get_active_theme
from utils import css_injector as brand

def get_plotly_layout(title: str = "") -> dict:
    """Return a Plotly layout dict that matches the active Snowsight theme."""
    theme = get_active_theme()
    is_dark = theme == "dark"

    return dict(
        title=dict(text=title, font=dict(size=16, color=brand.TA_TEXT_DARK if is_dark else brand.TA_TEXT_LIGHT)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family="Source Sans Pro, sans-serif",
            color=brand.TA_TEXT_DARK if is_dark else brand.TA_TEXT_LIGHT,
        ),
        colorway=[
            brand.TA_ORANGE, "#2196F3", "#4CAF50", "#FF9800",
            "#9C27B0", "#00BCD4", "#E91E63", "#8BC34A",
        ],
        xaxis=dict(
            gridcolor="#2D333B" if is_dark else "#E0E0E0",
            tickfont=dict(color=brand.TA_TEXT_DARK if is_dark else brand.TA_TEXT_LIGHT),
            title=dict(font=dict(color=brand.TA_TEXT_DARK if is_dark else brand.TA_TEXT_LIGHT)),
        ),
        yaxis=dict(
            gridcolor="#2D333B" if is_dark else "#E0E0E0",
            tickfont=dict(color=brand.TA_TEXT_DARK if is_dark else brand.TA_TEXT_LIGHT),
            title=dict(font=dict(color=brand.TA_TEXT_DARK if is_dark else brand.TA_TEXT_LIGHT)),
        ),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=brand.TA_TEXT_DARK if is_dark else brand.TA_TEXT_LIGHT)),
        margin=dict(l=40, r=20, t=50, b=40),
    )
```

### 6.3 Chart Theming — Altair

```python
# components/chart_theme.py (continued)
import altair as alt

def register_ta_altair_theme():
    """Register and enable a Tiger Analytics Altair theme."""
    theme = get_active_theme()
    is_dark = theme == "dark"

    def _ta_theme():
        return {
            "config": {
                "background": "transparent",
                "title": {"color": brand.TA_TEXT_DARK if is_dark else brand.TA_TEXT_LIGHT},
                "axis": {
                    "labelColor": brand.TA_GREY_700 if not is_dark else "#8B949E",
                    "titleColor": brand.TA_TEXT_DARK if is_dark else brand.TA_TEXT_LIGHT,
                    "gridColor": "#2D333B" if is_dark else "#E0E0E0",
                },
                "range": {
                    "category": [
                        brand.TA_ORANGE, "#2196F3", "#4CAF50", "#FF9800",
                        "#9C27B0", "#00BCD4", "#E91E63", "#8BC34A",
                    ]
                },
            }
        }

    alt.themes.register("tiger_analytics", _ta_theme)
    alt.themes.enable("tiger_analytics")
```

### 6.4 Branded Footer

```python
# components/footer.py
import streamlit as st
from utils.theme_detect import get_active_theme
from utils.css_injector import TA_ORANGE, TA_GREY_700

def render_footer():
    theme = get_active_theme()
    text_color = "#8B949E" if theme == "dark" else TA_GREY_700
    st.markdown("---")
    st.markdown(
        f'<p style="text-align:center; color:{text_color}; font-size:0.8rem;">'
        f'Powered by <span style="color:{TA_ORANGE}; font-weight:600;">Tiger Analytics</span>'
        f' · Built on Snowflake</p>',
        unsafe_allow_html=True,
    )
```

---

## 7. Layout Patterns

### Dashboard Layout

```python
st.set_page_config(page_title="TA Dashboard", layout="wide")

# 1. Inject CSS FIRST (this is the primary theming mechanism)
inject_global_css()

# 2. Header
render_header("Supply Chain Dashboard")

# 3. KPI Row
render_kpi_row([
    {"label": "Total Revenue", "value": "$12.4M", "delta": "+8.2%"},
    {"label": "Active SKUs",   "value": "3,421",  "delta": "-12"},
    {"label": "Forecast MAPE", "value": "4.7%",   "delta": "-0.3%"},
])

# 4. Charts in columns
col_left, col_right = st.columns([2, 1])
with col_left:
    st.plotly_chart(fig_trend, use_container_width=True)
with col_right:
    st.plotly_chart(fig_donut, use_container_width=True)

# 5. Data table
st.dataframe(df, use_container_width=True)

# 6. Footer
render_footer()
```

### Multi-Page App

```python
# streamlit_app.py
import streamlit as st
from components.header import render_header
from components.sidebar import render_sidebar
from utils.css_injector import inject_global_css

st.set_page_config(page_title="TA Analytics", layout="wide")
inject_global_css()
render_sidebar()
render_header("Analytics Platform")
```

---

## 8. Do's and Don'ts

### DO

- Use **Python CSS injection** (`inject_global_css()`) as the primary theming mechanism.
- Call `inject_global_css()` **once**, immediately after `st.set_page_config()`.
- Test every app in **both** Snowsight Light and Dark modes before delivery.
- Rely on automatic theme detection via `st.get_option("theme.backgroundColor")` — no manual toggle needed.
- Use `st.set_page_config(layout="wide")` for dashboards.
- Center-align the Tiger Analytics logo in headers or left-align in sidebar.
- Use Tiger Orange (`#F15A22`) as the primary accent — buttons, links, chart highlights.
- Use transparent chart backgrounds so they adapt to any theme.
- Use `streamlit-extras` `stylable_container` for advanced card layouts (verify SiS compatibility).
- Validate all packages against the Snowflake Anaconda channel (warehouse) or PyPI via EAI (container).
- Centralize ALL CSS in `css_injector.py` — one function, one call.

### DON'T

- **Do NOT rely on `config.toml` `[theme]` blocks** — they have limited/no support in SiS warehouse runtimes.
- Hard-code `background-color: white` or `color: black` — these break in Dark mode.
- Use fonts not available in Snowsight (no Google Fonts CDN — CSP blocks external domains).
- Use `st.html()` for content that could be done with native components.
- Import packages not in the Snowflake Anaconda channel without checking first.
- Use gradient backgrounds or heavy visual effects — keep it data-professional.
- Scatter `st.markdown("<style>...")` across multiple files — consolidate in `css_injector.py`.
- Use Tiger Analytics logo at widths smaller than 80px or on busy backgrounds.
- Forget to provide alt-text for images in `st.image()`.

---

## 9. Validation Checklist

Before shipping any app, verify:

| Check                                      | Pass? |
| ------------------------------------------ | ----- |
| App renders correctly in Snowsight **Light** mode |       |
| App renders correctly in Snowsight **Dark** mode  |       |
| Logo switches correctly between themes     |       |
| All charts use transparent backgrounds     |       |
| KPI cards have branded left-border accent  |       |
| Primary buttons use Tiger Orange           |       |
| Footer displays "Powered by Tiger Analytics" |     |
| All text meets WCAG AA contrast ratios     |       |
| No external CDN dependencies               |       |
| Packages verified against Anaconda channel |       |
| `inject_global_css()` is called once, right after `st.set_page_config()` |  |
| Auto theme detection adapts to Snowsight Light/Dark/System |  |
| Sidebar colors and text are readable in both themes |  |
| Page title and favicon are set             |       |

---

## 10. Snowflake Session Establishment

Every SiS app must establish a Snowpark session. Use a **multi-strategy fallback** that works across warehouse runtime, container runtime, and local development:

```python
IN_SIS = False
session = None
try:
    from snowflake.snowpark.context import get_active_session
    session = get_active_session(); IN_SIS = True
except Exception: pass
if session is None:
    try:
        conn = st.connection("snowflake"); session = conn.session(); IN_SIS = True
    except Exception: pass
if session is None:
    try:
        from snowflake.snowpark import Session
        session = Session.builder.config('connection_name', 'default').create()
    except Exception:
        st.error("Could not establish Snowflake connection."); st.stop()
```

> **Key**: Try `get_active_session()` first (warehouse runtime), then `st.connection` (SiS), then a local Session builder. Always call `st.stop()` if all strategies fail.

---

## 11. Data-Fetching Patterns

### 11.1 Cached Query Helpers

Use `@st.cache_data` with appropriate TTLs to avoid redundant Snowflake queries:

```python
@st.cache_data(ttl=900, show_spinner=False)
def run_query(_session, query):
    """Standard cached query — 15 min TTL for frequently changing data."""
    return _session.sql(query).to_pandas()

@st.cache_data(ttl=1800, show_spinner=False)
def run_query_slow(_session, query):
    """Long-TTL cache for expensive/stable queries (storage, serverless, SPCS)."""
    return _session.sql(query).to_pandas()
```

> **Convention**: Prefix the session parameter with `_` so Streamlit skips hashing it.

### 11.2 Safe Value Extraction

When reading Snowflake aggregation results, always guard against `None`:

```python
def sv(val, default=0):
    if val is None: return default
    try: return float(val)
    except: return default
```

---

## 12. Altair Chart Helpers

The real-world Cost Tower app uses reusable Altair chart factories. Adopt these for consistency:

### 12.1 Horizontal Bar Chart

```python
def bar_h(df, x, y, color, xt, yt, h=280, fmt=',.2f'):
    return alt.Chart(df).mark_bar(color=color, cornerRadiusEnd=3).encode(
        x=alt.X(f'{x}:Q', title=xt, axis=alt.Axis(format=fmt, labelFontSize=11, titleFontSize=12)),
        y=alt.Y(f'{y}:N', sort='-x', title=yt, axis=alt.Axis(labelFontSize=11, titleFontSize=12, labelLimit=180)),
        tooltip=[alt.Tooltip(f'{y}:N', title=yt), alt.Tooltip(f'{x}:Q', title=xt, format=fmt)]
    ).properties(height=h).configure_view(strokeWidth=0)
```

### 12.2 Vertical Bar Chart (Time Series)

```python
def bar_v(df, x, y, color, xt, yt, h=280, fmt=',.2f'):
    return alt.Chart(df).mark_bar(color=color, cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        x=alt.X(f'{x}:T', title=xt, axis=alt.Axis(labelFontSize=11, titleFontSize=12, labelAngle=-30)),
        y=alt.Y(f'{y}:Q', title=yt, axis=alt.Axis(format=fmt, labelFontSize=11, titleFontSize=12)),
        tooltip=[alt.Tooltip(f'{x}:T', title='Date'), alt.Tooltip(f'{y}:Q', title=yt, format=fmt)]
    ).properties(height=h).configure_view(strokeWidth=0)
```

### 12.3 Donut Chart

```python
def donut(df, theta_col, color_col, palette, h=280):
    return alt.Chart(df).mark_arc(innerRadius=45, outerRadius=100).encode(
        theta=f'{theta_col}:Q',
        color=alt.Color(f'{color_col}:N', scale=alt.Scale(range=palette),
                        legend=alt.Legend(title=color_col, labelFontSize=11)),
        tooltip=[alt.Tooltip(f'{color_col}:N'), alt.Tooltip(f'{theta_col}:Q', format=',.2f')]
    ).properties(height=h)
```

> **Key conventions**: Always set `strokeWidth=0` on bar charts, use `cornerRadius` for rounded bars, set `labelLimit=180` for horizontal bars to prevent label truncation, and keep height at `280` for consistent card-level sizing.

---

## 13. Styled Section Headers & Callout Components

The Cost Tower app uses custom HTML components for section headers and recommendation callouts. These provide better visual hierarchy than plain `st.markdown("###")`.

### 13.1 Section Headers with Accent Border

```python
def sh(title, style="blue", tooltip=""):
    """Render a styled section header with color-coded left border.

    Args:
        style: 'blue' (info), 'warn' (amber), 'green' (success)
        tooltip: Optional help icon with hover text
    """
    colors = {
        "blue":  ("linear-gradient(90deg,#f1f5f9,#fff)", "#3b82f6", "#1e293b"),
        "warn":  ("linear-gradient(90deg,#fefce8,#fff)", "#f59e0b", "#92400e"),
        "green": ("linear-gradient(90deg,#f0fdf4,#fff)", "#22c55e", "#166534"),
    }
    bg, border, text = colors.get(style, colors["blue"])
    tip = f' <span title="{tooltip}" style="cursor:help;font-size:0.75rem;opacity:0.5;">ℹ️</span>' if tooltip else ""
    st.markdown(
        f'<div style="background:{bg};border-left:4px solid {border};padding:10px 16px;'
        f'border-radius:0 8px 8px 0;margin:14px 0 8px 0;font-weight:600;font-size:0.93rem;'
        f'color:{text}">{title}{tip}</div>',
        unsafe_allow_html=True,
    )
```

### 13.2 Recommendation Callouts

```python
def rec(text, style="info"):
    """Render a styled recommendation/callout box.

    Args:
        style: 'info' (blue), 'warn' (amber), 'ok' (green)
    """
    palettes = {
        "info": ("#eff6ff", "#bfdbfe", "#1e40af", "💡"),
        "warn": ("#fef9c3", "#fde68a", "#92400e", "⚠️"),
        "ok":   ("#f0fdf4", "#bbf7d0", "#166534", "✅"),
    }
    bg, border, color, icon = palettes.get(style, palettes["info"])
    import re
    cleaned = re.sub(
        r'`([^`]+)`',
        r'<code style="background:rgba(0,0,0,0.06);padding:1px 5px;border-radius:3px;'
        r'font-size:0.78rem;font-family:monospace;">\1</code>',
        text,
    )
    st.markdown(
        f'<div style="background:{bg};border:1px solid {border};border-left:4px solid {color};'
        f'border-radius:0 8px 8px 0;padding:10px 14px;margin:6px 0;font-size:0.84rem;'
        f'color:{color};line-height:1.5;">{icon} {cleaned}</div>',
        unsafe_allow_html=True,
    )
```

### 13.3 Pass/Fail Governance Badges

```python
def gov(label, passed, detail=""):
    tag = 'background:#dcfce7;color:#166534' if passed else 'background:#fee2e2;color:#991b1b'
    icon = '✅' if passed else '❌'
    st.markdown(
        f'{icon} **{label}** <span style="{tag};padding:2px 10px;border-radius:6px;'
        f'font-size:0.78rem;font-weight:600;">{"PASS" if passed else "FAIL"}</span> {detail}',
        unsafe_allow_html=True,
    )
```

---

## 14. Sidebar Navigation with Tab Toggles

For complex dashboards with many tabs, use a **sidebar toggle pattern** that lets users enable/disable tabs:

```python
with st.sidebar:
    st.markdown("## ❄️ App Title")
    st.markdown("---")

    ALL_TABS = {
        "dashboard":    {"icon": "📊", "label": "Dashboard"},
        "optimization": {"icon": "⚡", "label": "Optimization"},
        "governance":   {"icon": "🛡️", "label": "Governance"},
    }

    st.markdown("### 🧭 Navigation")
    enabled = {}
    for k, v in ALL_TABS.items():
        enabled[k] = st.toggle(f"{v['icon']}  {v['label']}", value=True, key=f"t_{k}")

    st.markdown("---")
    st.markdown("### ⚙️ Settings")
    period = st.selectbox("Default Period", ["7 Days", "14 Days", "30 Days", "90 Days"], index=2)
    days = int(period.split()[0])

active = [k for k, v in enabled.items() if v]
labels = [f"{ALL_TABS[k]['icon']}  {ALL_TABS[k]['label']}" for k in active]
if not active:
    st.info("Enable at least one tab.")
    st.stop()
tabs = st.tabs(labels)
tm = dict(zip(active, tabs))

if "dashboard" in tm:
    with tm["dashboard"]:
        # ... dashboard content
        pass
```

> **Key**: This pattern decouples sidebar config from tab rendering. Users control which tabs are visible, and the app only renders enabled tabs — reducing query load for unused sections.

---

## 15. Cortex AI Integration Pattern

For on-demand AI-powered analysis within dashboards, use a button-triggered Cortex Complete call:

```python
CORTEX_AVAILABLE = False
Complete = None
try:
    from snowflake.cortex import Complete as _Complete
    Complete = _Complete; CORTEX_AVAILABLE = True
except ImportError:
    pass

# SQL fallback for Container Runtime (where snowflake.cortex may not be importable)
if not CORTEX_AVAILABLE:
    try:
        session.sql("SELECT SNOWFLAKE.CORTEX.COMPLETE('mistral-large2','test') AS R").collect()
        CORTEX_AVAILABLE = True
        def Complete(model, prompt, session=None):
            safe = prompt.replace("'", "''")
            r = session.sql(f"SELECT SNOWFLAKE.CORTEX.COMPLETE('{model}','{safe}') AS R").collect()
            return r[0]['R'] if r else ""
    except Exception:
        pass

def ai_rec_button(key, data_summary, context):
    """On-demand AI analysis button. Only renders when Cortex is available."""
    if not CORTEX_AVAILABLE:
        return
    if st.button("🤖 Get AI Analysis", key=key):
        with st.spinner("Analyzing with AI..."):
            try:
                prompt = f"""You are a Snowflake expert. Analyze this data and give 3 actionable recommendations.
Context: {context}
Data:
{data_summary}"""
                result = Complete("mistral-large2", prompt, session=session)
                st.markdown(result, unsafe_allow_html=True)
            except Exception as e:
                st.warning(f"AI analysis error: {str(e)[:150]}")
```

> **Key**: Always provide the SQL-based fallback for `Complete` — the Python `snowflake.cortex` package may not be importable on Container Runtime even though the SQL function works. Guard all AI buttons with `CORTEX_AVAILABLE` so they degrade gracefully.

---

## 16. Single-File App Structure

Not every app needs the multi-file structure from §3. For smaller dashboards (< 500 lines), a **single-file pattern** is appropriate:

```python
# streamlit_app.py — self-contained single-file app

import streamlit as st
import pandas as pd
import altair as alt

# 1. Page config
st.set_page_config(page_title="TA Dashboard", layout="wide")

# 2. Brand tokens (inline — no separate file needed)
TA_ORANGE = "#F15A22"
# ... other tokens

# 3. Theme detection (inline)
def get_active_theme() -> str:
    # ... same logic as §4.2
    pass

# 4. CSS injection (inline)
THEME = get_active_theme()
IS_DARK = THEME == "dark"
st.markdown(f"""<style>...</style>""", unsafe_allow_html=True)

# 5. Session
session = None
try:
    from snowflake.snowpark.context import get_active_session
    session = get_active_session()
except: pass
# ... fallbacks

# 6. Helpers, layout, content
# ...
```

Use single-file when:
- App is a focused dashboard with 1-3 views
- No shared components across multiple apps
- Rapid prototyping or POC stage

Graduate to multi-file (§3) when:
- App exceeds ~500 lines
- Multiple pages share components
- Team needs separate ownership of modules

---

## 17. Production CSS Patterns (from Real Deployments)

The Cost Tower app demonstrates several CSS patterns not covered by the basic `inject_global_css()`. Add these to your CSS injection as needed:

### Metric Card Hover Effects

```css
[data-testid="stMetric"] {
    background: linear-gradient(135deg, #f8f9fc 0%, #eef1f8 100%);
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 14px 18px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    transition: transform 0.15s;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-1px);
    box-shadow: 0 3px 8px rgba(0,0,0,0.06);
}
```

### Metric Label & Value Sizing

```css
[data-testid="stMetricLabel"] {
    font-size: 0.76rem !important;
    color: #64748b !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.3px;
}
[data-testid="stMetricValue"] {
    font-size: 1.3rem !important;
    font-weight: 700 !important;
}
```

### Tab Styling

```css
.stTabs [data-baseweb="tab-list"] {
    gap: 2px;
    flex-wrap: wrap;
    border-bottom: 2px solid #e2e8f0;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px 8px 0 0;
    padding: 8px 16px;
    font-size: 0.82rem;
    font-weight: 600;
    transition: all 0.2s;
}
```

### Chat Message Styling

```css
div[data-testid="stChatMessage"] {
    border-radius: 12px;
    border: 1px solid #e2e8f0;
    margin-bottom: 8px;
}
```

> **Note**: These are light-mode defaults from the Cost Tower. Adapt them with theme-aware tokens for dark mode support.

---

## 18. Quick-Start Template

For a minimal branded app, use the template at `templates/starter_app.py`. It includes the header, footer, CSS injection, theme detection, and a sample KPI + chart layout — all wired up and ready to deploy to Snowflake.
