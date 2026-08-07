# Snowsight Theming Reference — Streamlit in Snowflake

This document covers the specifics of how Streamlit apps behave inside Snowsight regarding dark mode, light mode, and system appearance preferences.

---

## 1. How Snowsight Determines Theme

Snowsight supports three appearance modes accessible via **user preferences**:

| Mode     | Behavior                                                         |
| -------- | ---------------------------------------------------------------- |
| **Light**  | Forces light theme regardless of OS preference.                |
| **Dark**   | Forces dark theme regardless of OS preference.                 |
| **System** | Inherits from the user's OS/browser `prefers-color-scheme`.    |

When a Streamlit app runs inside Snowsight, Snowsight **propagates the resolved theme** into the Streamlit iframe. This means `st.get_option("theme.backgroundColor")` returns the resolved background color — whether the user chose Light, Dark, or System mode. Your app auto-detects theme without needing a manual toggle.

---

## 2. Theming Strategy: Python CSS Injection (NOT config.toml)

> **CRITICAL**: `config.toml` `[theme]` blocks have **limited support in SiS warehouse runtimes** and incomplete support in container runtimes. The newer `[theme.light]` / `[theme.dark]` dual-theme blocks are NOT reliably supported in Snowflake.

**The primary theming approach is pure Python CSS injection** via `st.markdown(unsafe_allow_html=True)`. This works reliably across both warehouse and container runtimes.

### Optional Minimal config.toml

You may include a minimal `config.toml` for `primaryColor` only as a supplementary measure. Do not rely on it for backgrounds, text colors, or sidebar theming.

```toml
# .streamlit/config.toml — OPTIONAL, minimal safe subset
[theme]
primaryColor = "#F15A22"
```

### Full Theming via Python

All backgrounds, text colors, sidebar colors, component styling, and theme switching are handled by `css_injector.py`. See SKILL.md §5 for the complete implementation.

---

## 3. Runtime Theme Detection

Snowsight propagates its resolved theme into the Streamlit iframe. Use `st.get_option("theme.backgroundColor")` to read the resolved value:

```python
import streamlit as st

def detect_snowsight_theme() -> str:
    """Detect the active theme in the current Snowsight session.

    Snowsight injects the resolved theme (including System/OS preference)
    into the Streamlit iframe. st.get_option reads the resolved value.
    No manual toggle is needed.
    """
    try:
        bg = st.get_option("theme.backgroundColor")
        if bg:
            hex_color = bg.lstrip("#")
            r, g, b = (int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            return "dark" if luminance < 0.5 else "light"
    except Exception:
        pass
    return "light"
```

### CSS Media Query Approach (supplementary)

For elements rendered via `st.markdown(unsafe_allow_html=True)`, you can use CSS `prefers-color-scheme` as an additional layer:

```html
<style>
  .ta-logo-light { display: block; }
  .ta-logo-dark  { display: none; }

  @media (prefers-color-scheme: dark) {
    .ta-logo-light { display: none; }
    .ta-logo-dark  { display: block; }
  }
</style>
```

> **Note**: The CSS media query approach only responds to the OS/browser preference. For users who manually set Snowsight to Light or Dark (overriding OS), the Python detection via `st.get_option` is authoritative.

---

## 4. Common Pitfalls

### 4.1 Hard-Coded Colors

**Problem**: Using `color: black` or `background: white` directly in CSS.
**Impact**: Text becomes invisible or unreadable in Dark mode.
**Fix**: Always use theme-relative colors via tokens.

```python
# BAD
st.markdown('<p style="color: black;">Hello</p>', unsafe_allow_html=True)

# GOOD
from utils.theme_detect import get_active_theme
text_color = "#E6EDF3" if get_active_theme() == "dark" else "#1A1A2E"
st.markdown(f'<p style="color: {text_color};">Hello</p>', unsafe_allow_html=True)
```

### 4.2 Chart Backgrounds

**Problem**: Plotly/Altair default backgrounds (white) clash with Dark mode.
**Fix**: Always set chart backgrounds to transparent.

```python
# Plotly
fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")

# Altair
alt.Chart(...).configure(background="transparent")
```

### 4.3 Image Logos on Wrong Background

**Problem**: Dark logo on dark background is invisible.
**Fix**: Swap logo based on detected theme (see SKILL.md §4.3).

### 4.4 Streamlit Native Components

Since we use CSS injection (not `config.toml`) for theming, some native components like `st.metric`, `st.dataframe`, and `st.tabs` may need explicit CSS overrides to match the brand. The `inject_global_css()` function in SKILL.md §5 already covers the most common components. If you find a component that doesn't inherit the theme, add its CSS selector to `inject_global_css()` — never in a separate `st.markdown` block.

### 4.5 External Font Loading

**Problem**: `@import url('https://fonts.googleapis.com/...')` fails in SiS due to CSP restrictions.
**Impact**: App falls back to browser default fonts, breaking visual consistency.
**Fix**: Use the Snowflake-safe font stack: `'Source Sans Pro', 'Segoe UI', sans-serif`.

---

## 5. Snowsight-Specific CSS Selectors

These CSS selectors are used to target specific Streamlit elements. They may change between Streamlit versions — test after upgrades.

| Target                    | Selector                                          |
| ------------------------- | ------------------------------------------------- |
| App container             | `.stApp`                                          |
| Main content area         | `[data-testid="stAppViewContainer"]`              |
| Sidebar                   | `section[data-testid="stSidebar"]`                |
| Metric widget             | `div[data-testid="stMetric"]`                     |
| Metric value              | `div[data-testid="stMetricValue"]`                |
| Metric label              | `div[data-testid="stMetricLabel"]`                |
| Metric delta              | `div[data-testid="stMetricDelta"]`                |
| Dataframe                 | `div[data-testid="stDataFrame"]`                  |
| Tab container             | `.stTabs`                                         |
| Tab list                  | `.stTabs [data-baseweb="tab-list"]`               |
| Active tab                | `.stTabs [aria-selected="true"]`                  |
| Button                    | `.stButton > button`                              |
| Download button           | `.stDownloadButton > button`                      |
| Chat message              | `div[data-testid="stChatMessage"]`                |
| Sidebar header            | `section[data-testid="stSidebar"] > div:first-child` |
| Block container (top gap) | `div.block-container`                             |

---

## 6. Testing Procedure

Before deploying any app, perform this theme validation:

1. **Light mode**: In Snowsight → Settings → Appearance → Light. Verify the full app.
2. **Dark mode**: Switch to Dark. Verify the full app — pay attention to logos, chart backgrounds, text contrast, card borders.
3. **System mode**: Switch to System. Toggle your OS appearance preference to confirm the app follows.
4. **Sidebar**: Verify sidebar branding, navigation labels, and contrast in both themes.
5. **Charts**: Confirm all chart backgrounds are transparent and series colors are visible in both themes.
6. **Mobile**: If the app may be viewed on mobile Snowsight, verify responsive layout.
