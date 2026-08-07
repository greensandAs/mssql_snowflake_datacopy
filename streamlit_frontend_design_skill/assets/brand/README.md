# Brand Assets

This directory contains programmatic brand tokens for Tiger Analytics Streamlit apps.

## Files

| File              | Description                                           |
| ----------------- | ----------------------------------------------------- |
| `brand_tokens.py` | Python module with all brand colors, fonts, palettes  |

## Usage

```python
from assets.brand.brand_tokens import BRAND, get_theme_tokens

# Access a specific token
primary_color = BRAND["orange"]  # "#F15A22"

# Get all tokens resolved for a theme
tokens = get_theme_tokens("dark")
bg_color = tokens["bg"]          # "#0D1117"
```

## Updating

When the brand team issues new guidelines:

1. Update the hex values in `brand_tokens.py`
2. Mirror the changes in `references/BRAND_SYSTEM.md`
3. Update `templates/config.toml` accordingly
4. Notify all teams using this skill to retest their apps
