# ta-streamlit-design

**Tiger Analytics — Streamlit in Snowflake Design Skill for Cortex Code**

A company-wide skill that guides Cortex Code (and Claude Code) to produce brand-compliant, theme-adaptive Streamlit apps running inside Snowflake Snowsight.

---

## What This Skill Does

When invoked, this skill instructs the AI coding agent to:

- Apply the **Tiger Analytics brand system** — colors, typography, logo placement
- Generate **theme-adaptive apps** that auto-detect Snowsight Light, Dark, and System modes
- Use **pure Python CSS injection** as the primary theming mechanism (not config.toml)
- Use **Snowflake-compatible** packages and patterns (Anaconda channel, CSP-safe CSS)
- Follow **consistent project structure** across all Tiger Analytics Streamlit apps
- Produce **branded components** — headers, footers, KPI cards, chart themes (Plotly + Altair)
- Establish **Snowflake sessions** with multi-strategy fallback (warehouse + container + local)
- Integrate **Cortex AI** with graceful degradation across runtime environments
- Use **cached query helpers** and safe value extraction patterns

---

## Folder Structure

```
ta-streamlit-design/
├── SKILL.md                          # Main skill instructions (Cortex Code reads this)
├── README.md                         # This file
├── references/
│   ├── BRAND_SYSTEM.md               # Color tokens, chart palettes, typography, logo rules
│   ├── SNOWSIGHT_THEMING.md          # Dark/light/system mode handling patterns
│   └── FAQ.md                        # Troubleshooting common issues
├── assets/
│   ├── brand/
│   │   └── brand_tokens.py           # Importable Python module with all brand tokens
│   └── logos/
│       ├── ta_logo_light.svg         # ⚠️  PLACEHOLDER — replace with official
│       ├── ta_logo_dark.svg          # ⚠️  PLACEHOLDER — replace with official
│       ├── ta_logo_monochrome.svg    # ⚠️  PLACEHOLDER — replace with official
│       └── README.md                 # Instructions for replacing logos
└── templates/
    ├── config.toml                   # OPTIONAL — minimal primaryColor only
    └── starter_app.py                # Full working branded app template
```

---

## Installation

### Cortex Code CLI (CoCo)

**Project-level** (recommended for team-wide use):

```bash
# From your project root
mkdir -p .cortex/skills
cp -r ta-streamlit-design .cortex/skills/
```

**Global** (available across all projects for an individual user):

```bash
mkdir -p ~/.cortex/skills
cp -r ta-streamlit-design ~/.cortex/skills/
```

**From a Git repository** (if hosted):

```bash
npx skills add https://github.com/your-org/ta-streamlit-design
```

### Cortex Code in Snowsight

1. Open a **Workspace** in Snowsight.
2. Navigate to the Cortex Code assistant panel.
3. Upload the skill by placing the `ta-streamlit-design/` directory in your workspace's `.snowflake/cortex/skills/` path.

### Claude Code

The skill is compatible with Claude Code. Place it in your Claude Code skills directory:

```bash
mkdir -p ~/.claude/skills
cp -r ta-streamlit-design ~/.claude/skills/
```

---

## Usage

Once installed, invoke the skill in Cortex Code:

```
/skill ta-streamlit-design
```

Then prompt naturally:

> "Build a supply chain dashboard with KPIs for revenue, fill rate, and forecast accuracy. Include a trend chart and a data table."

The agent will follow the skill's instructions to produce a fully branded, theme-adaptive Streamlit app.

### Example Prompts

| Prompt | What the Skill Does |
|--------|---------------------|
| "Create a new Streamlit dashboard for customer churn analysis" | Scaffolds a full app with branded header, KPI cards, charts, and footer |
| "Add dark mode support to my existing Streamlit app" | Adds CSS injection, auto theme detection, and logo switching |
| "Style this chart to match Tiger Analytics branding" | Applies brand color palette, transparent backgrounds, and proper fonts |
| "Add a branded sidebar with navigation" | Creates sidebar with logo, accent stripe, and radio navigation |
| "Make this app look professional for a client demo" | Full brand treatment — header, footer, KPI styling, chart theme, layout |
| "Add Cortex AI analysis to this dashboard" | Adds button-triggered AI recommendations with SQL fallback |

---

## ⚠️ Before First Use — Replace Logos

The logos in `assets/logos/` are **placeholders**. Before deploying any app:

1. Obtain official Tiger Analytics logo files from the Marketing & Communications team.
2. Export variants as SVG with transparent backgrounds.
3. Replace the placeholder files, keeping the same filenames.
4. Add a 32×32 PNG favicon as `assets/logos/ta_favicon.png`.

See `assets/logos/README.md` for detailed instructions.

---

## Updating the Brand

If Tiger Analytics updates its brand guidelines:

1. Update color values in `references/BRAND_SYSTEM.md`
2. Update the Python tokens in `assets/brand/brand_tokens.py`
3. Update `templates/config.toml` if primaryColor changed
4. Replace logo files if the logo was redesigned
5. Run a visual regression test on existing apps

---

## SKILL.md Section Overview

| Section | Topic |
|---------|-------|
| §1–§3   | Design principles, checklist, project structure |
| §4      | Theme config: why not config.toml, auto detection, logo switching |
| §5      | CSS injection — primary theming mechanism |
| §6      | Component patterns: KPIs, Plotly, Altair, footer |
| §7      | Layout patterns: dashboard, multi-page |
| §8–§9   | Do's/Don'ts, validation checklist |
| §10     | Snowflake session establishment (multi-strategy) |
| §11     | Cached query helpers, safe value extraction |
| §12     | Altair chart factories (bar_h, bar_v, donut) |
| §13     | Styled section headers & callout components |
| §14     | Sidebar navigation with tab toggles |
| §15     | Cortex AI integration with SQL fallback |
| §16     | Single-file vs multi-file app structure |
| §17     | Production CSS patterns from real deployments |
| §18     | Quick-start template reference |

---

## Compatibility

| Component                   | Version / Requirement              |
| --------------------------- | ---------------------------------- |
| Streamlit                   | 1.28+ (SiS-compatible)            |
| Streamlit in Snowflake      | GA (all commercial clouds)         |
| Cortex Code CLI             | 1.0+                              |
| Claude Code                 | Compatible                         |
| streamlit-extras            | ≤ 0.2.7 (Anaconda channel limit)  |
| Python                      | 3.8+ (SiS default)                |

---

## Contributing

1. Test changes in **both** Snowsight Light and Dark modes.
2. Validate all packages against the Snowflake Anaconda channel.
3. Update `references/` docs if you change tokens or patterns.
4. Keep the starter template in sync with any SKILL.md changes.

---

## License

Internal use — Tiger Analytics. Not for external distribution without approval from the Tiger Analytics Marketing & Communications team.
