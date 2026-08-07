# FAQ & Troubleshooting

Common issues when building Tiger Analytics branded Streamlit apps in Snowflake.

---

## Theming Issues

### Q: My custom CSS works locally but not in Snowsight

**Cause**: Streamlit in Snowflake restricts certain HTML/CSS features via Content Security Policy (CSP). Native Apps have stricter limits than SiS apps.

**Fix**:
- Verify `unsafe_allow_html=True` is enabled on all `st.markdown()` calls.
- Avoid `@import`, `<link>` to external stylesheets, and inline `<script>` tags.
- For Native Apps, Custom UI support must be enabled (private preview).

### Q: Dark mode shows white flashes on page load

**Cause**: Streamlit renders the default (light) theme briefly before the Python CSS injection runs.

**Fix**: This is a known Streamlit behavior. The CSS injection approach minimizes it, but a brief flash may still occur. If your runtime supports it, include a minimal `.streamlit/config.toml` with `primaryColor` to reduce the flash.

### Q: My chart colors look washed out in dark mode

**Cause**: Chart series colors were chosen for light backgrounds and lack sufficient contrast on dark surfaces.

**Fix**: Use the Tiger Analytics categorical palette defined in `BRAND_SYSTEM.md` — these colors were selected for visibility in both themes. Ensure chart backgrounds are set to `transparent`.

### Q: Logo appears but has a white box around it in dark mode

**Cause**: The SVG or PNG logo has an opaque white background baked into the file.

**Fix**: Use the SVG logos in `assets/logos/` which have transparent backgrounds. If you must use PNG, ensure it was exported with transparency.

### Q: Theme detection returns "light" even when Snowsight is in dark mode

**Cause**: `st.get_option("theme.backgroundColor")` may return `None` in some edge cases during initial load.

**Fix**: The `get_active_theme()` function falls back to "light" when detection fails. This is the safe default since Snowsight defaults to light. On subsequent reruns the resolved value is available. If your app absolutely needs dark mode on first render, check if the `theme.base` option is set to `"dark"`.

---

## Package Issues

### Q: `streamlit-extras` is not available or fails to install

**Fix**: `streamlit-extras` is available in the Snowflake Anaconda channel up to version `0.2.7`. Add it via the Snowsight package installer or `environment.yml`. Versions beyond 0.2.7 may not be available.

### Q: I need a package not in the Anaconda channel

**Fix (warehouse runtime)**: You cannot pip-install arbitrary packages. Check the Snowflake Anaconda channel catalog. If unavailable, implement the functionality in pure Python or use a Snowflake UDF.

**Fix (container runtime)**: Set up an External Access Integration (EAI) to install from PyPI. See Snowflake docs on dependency management for container runtimes.

---

## Session Issues

### Q: `get_active_session()` fails in container runtime

**Cause**: `get_active_session()` is only available in warehouse runtimes (it runs inside a stored procedure context).

**Fix**: Use the multi-strategy session fallback from SKILL.md §10. In container runtimes, `st.connection("snowflake")` is the correct approach.

### Q: `_snowflake` module not found

**Cause**: The `_snowflake` module is a private module only available in warehouse runtimes (UDF/stored procedure context). Container runtimes don't have it.

**Fix**: Replace `_snowflake.get_generic_secret_string()` with `st.secrets["secret_name"]`. See Snowflake docs on secrets in container runtimes.

---

## Layout Issues

### Q: My sidebar is too narrow for the logo

**Fix**: Set minimum sidebar width in CSS:
```python
st.markdown("""
<style>
    section[data-testid="stSidebar"] { min-width: 280px; }
</style>
""", unsafe_allow_html=True)
```

### Q: Content has a large gap at the top

**Fix**: The `inject_global_css()` already sets `padding-top: 1.5rem`. If you still see a gap, check for duplicate `st.set_page_config()` calls or extra `st.markdown` adding whitespace.

### Q: KPI cards are not the same height across columns

**Fix**: Use the `stylable_container` from `streamlit-extras` with a fixed `min-height`:
```python
from streamlit_extras.stylable_container import stylable_container

with stylable_container("kpi1", css_styles="{ min-height: 120px; }"):
    st.metric("Revenue", "$12.4M")
```

---

## Cortex AI Issues

### Q: `from snowflake.cortex import Complete` fails in container runtime

**Cause**: The `snowflake.cortex` Python package may not be importable in container runtimes, even though the SQL function works.

**Fix**: Use the SQL-based fallback pattern from SKILL.md §15. Call `SNOWFLAKE.CORTEX.COMPLETE()` via `session.sql()` instead.

---

## Deployment Issues

### Q: App works in Snowsight editor but fails when shared

**Cause**: The shared app may be running under a different role with different warehouse permissions.

**Fix**: Verify that the app's execution role has access to all referenced tables, stages, and warehouses.

### Q: `st.image()` cannot find my logo file

**Cause**: File paths in SiS are relative to the app's stage location, not the local filesystem.

**Fix**: Upload logo files to the app's stage. Reference them with the relative path from the app root (e.g., `"assets/logos/ta_logo_light.svg"`).
