# Tiger Analytics — Brand System Reference

This document defines the authoritative brand tokens for all Streamlit in Snowflake apps built by Tiger Analytics. All color values, typography choices, and logo usage rules in this file are derived from the Tiger Analytics corporate brand guidelines.

> **Maintainers**: Update this file when the brand team issues new guidelines. All downstream apps inherit from these tokens automatically via `assets/brand/brand_tokens.py`.

---

## 1. Color Palette

### Primary Colors

| Token Name          | Hex       | Role                                      |
| ------------------- | --------- | ----------------------------------------- |
| `TA_ORANGE`         | `#F15A22` | Primary brand accent — buttons, links, highlights |
| `TA_NAVY`           | `#1A1A2E` | Primary dark — headers, sidebar backgrounds |
| `TA_WHITE`          | `#FFFFFF` | Light mode backgrounds                    |

### Secondary Colors

| Token Name          | Hex       | Role                                      |
| ------------------- | --------- | ----------------------------------------- |
| `TA_ORANGE_DARK`    | `#D94E1C` | Hover/pressed state for orange elements   |
| `TA_ORANGE_LIGHT`   | `#FF7A47` | Light accent — tags, badges, subtle highlights |
| `TA_BLUE`           | `#2196F3` | Secondary chart color, info states        |
| `TA_GREEN`          | `#4CAF50` | Success states, positive deltas           |
| `TA_RED`            | `#E53935` | Error states, negative deltas             |
| `TA_AMBER`          | `#FF9800` | Warning states, caution indicators        |

### Neutral Scale

| Token Name          | Hex       | Role                                      |
| ------------------- | --------- | ----------------------------------------- |
| `TA_GREY_50`        | `#FAFAFA` | Lightest surface                          |
| `TA_GREY_100`       | `#F5F5F5` | Card backgrounds (light mode)             |
| `TA_GREY_200`       | `#E0E0E0` | Borders, dividers (light mode)            |
| `TA_GREY_400`       | `#9E9E9E` | Disabled text, placeholders               |
| `TA_GREY_700`       | `#4A4A68` | Body text (light mode)                    |
| `TA_GREY_900`       | `#1A1A2E` | Headings (light mode)                     |

### Dark Mode Tokens

| Token Name              | Hex       | Role                                  |
| ----------------------- | --------- | ------------------------------------- |
| `TA_DARK_BG`            | `#0D1117` | App background (dark mode)            |
| `TA_DARK_SURFACE`       | `#161B22` | Card/secondary backgrounds (dark mode)|
| `TA_DARK_BORDER`        | `#2D333B` | Borders, grid lines (dark mode)       |
| `TA_DARK_TEXT_PRIMARY`  | `#E6EDF3` | Primary text (dark mode)              |
| `TA_DARK_TEXT_SECONDARY`| `#8B949E` | Secondary/muted text (dark mode)      |

---

## 2. Chart Color Sequences

### Primary Sequence (8 colors)

Use this ordered sequence for categorical chart series:

```
#F15A22, #2196F3, #4CAF50, #FF9800, #9C27B0, #00BCD4, #E91E63, #8BC34A
```

### Sequential Palette (Orange ramp)

For heatmaps, choropleth maps, or sequential data:

```
#FFF3E0, #FFE0B2, #FFCC80, #FFB74D, #FFA726, #FF9800, #F15A22, #D94E1C
```

### Diverging Palette (Blue ← Neutral → Orange)

For positive/negative comparisons:

```
#1565C0, #42A5F5, #90CAF9, #E0E0E0, #FFCC80, #FF9800, #F15A22
```

---

## 3. Typography

### Snowflake-Safe Font Stack

Streamlit in Snowflake does not support loading external fonts (Google Fonts CDN is blocked). Use this font stack:

```
'Source Sans Pro', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif
```

- **Source Sans Pro** — Streamlit's default; available in SiS.
- **Segoe UI** — Windows fallback; clean and professional.
- **Helvetica Neue / Arial** — Universal fallback.

### Type Scale

| Element         | Size  | Weight | Token               |
| --------------- | ----- | ------ | -------------------- |
| Page Title      | 28px  | 700    | `st.title()`         |
| Section Header  | 22px  | 600    | `st.header()`        |
| Subsection      | 18px  | 600    | `st.subheader()`     |
| Body Text       | 14px  | 400    | `st.write()`         |
| Caption / Label | 12px  | 400    | `st.caption()`       |
| KPI Value       | 28px  | 700    | `st.metric()` value  |
| KPI Label       | 14px  | 400    | `st.metric()` label  |

---

## 4. Logo Usage

### Available Formats

| File                     | Use Case                                |
| ------------------------ | --------------------------------------- |
| `ta_logo_light.svg`      | On light/white backgrounds              |
| `ta_logo_dark.svg`       | On dark/navy backgrounds                |
| `ta_logo_monochrome.svg` | Single-color contexts (footers, prints) |
| `ta_favicon.png`         | Browser tab icon (32×32 PNG)            |

### Rules

1. **Minimum width**: 80px. Never display the logo smaller than this.
2. **Clear space**: Maintain padding equal to the height of the "T" in "Tiger" on all sides.
3. **Background**: Always place on a solid or near-solid background. Never overlay on busy images or gradients.
4. **Theme switching**: In Snowsight, detect the active theme and swap between `ta_logo_light.svg` (for light mode) and `ta_logo_dark.svg` (for dark mode).
5. **No modification**: Do not alter colors, proportions, rotation, or add effects to the logo.
6. **Placement**: Top-left of the header or centered in the sidebar header.

---

## 5. Spacing System

Use a consistent 4px base grid:

| Token     | Value | Usage                     |
| --------- | ----- | ------------------------- |
| `space-1` | 4px   | Tight internal padding    |
| `space-2` | 8px   | Element gaps              |
| `space-3` | 12px  | Card internal padding     |
| `space-4` | 16px  | Section gaps              |
| `space-6` | 24px  | Between major sections    |
| `space-8` | 32px  | Page-level margins        |

---

## 6. Iconography

Streamlit does not natively support icon libraries beyond emoji. For icons:

- Use Unicode emoji sparingly for page navigation labels (e.g., `📊 Overview`).
- In KPI cards, use emoji or short text labels — avoid importing icon fonts.
- For custom SVG icons in `st.markdown`, keep them monochrome and theme-adaptive.

---

## 7. brand_tokens.py — Python Reference

The file at `assets/brand/brand_tokens.py` exports all tokens as a Python dict for programmatic use:

```python
# assets/brand/brand_tokens.py
"""
Tiger Analytics brand tokens for Streamlit apps.
Import and use throughout your application for consistent branding.
"""

BRAND = {
    # Primary
    "orange":           "#F15A22",
    "navy":             "#1A1A2E",
    "white":            "#FFFFFF",

    # Secondary
    "orange_dark":      "#D94E1C",
    "orange_light":     "#FF7A47",
    "blue":             "#2196F3",
    "green":            "#4CAF50",
    "red":              "#E53935",
    "amber":            "#FF9800",

    # Neutrals
    "grey_50":          "#FAFAFA",
    "grey_100":         "#F5F5F5",
    "grey_200":         "#E0E0E0",
    "grey_400":         "#9E9E9E",
    "grey_700":         "#4A4A68",
    "grey_900":         "#1A1A2E",

    # Dark mode
    "dark_bg":          "#0D1117",
    "dark_surface":     "#161B22",
    "dark_border":      "#2D333B",
    "dark_text":        "#E6EDF3",
    "dark_text_muted":  "#8B949E",

    # Chart sequences
    "chart_categorical": [
        "#F15A22", "#2196F3", "#4CAF50", "#FF9800",
        "#9C27B0", "#00BCD4", "#E91E63", "#8BC34A",
    ],
    "chart_sequential_orange": [
        "#FFF3E0", "#FFE0B2", "#FFCC80", "#FFB74D",
        "#FFA726", "#FF9800", "#F15A22", "#D94E1C",
    ],
    "chart_diverging": [
        "#1565C0", "#42A5F5", "#90CAF9", "#E0E0E0",
        "#FFCC80", "#FF9800", "#F15A22",
    ],

    # Typography
    "font_stack": "'Source Sans Pro', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif",
}
```
