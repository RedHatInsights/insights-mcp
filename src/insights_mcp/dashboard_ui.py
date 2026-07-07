"""Shared helpers for Insights MCP dashboard UI resources."""

import base64
from importlib import resources
from pathlib import Path

PATTERNFLY_CSS_URL = "https://unpkg.com/@patternfly/patternfly@5.4.2/patternfly.min.css"
MCP_APPS_SDK_URL = "https://unpkg.com/@modelcontextprotocol/ext-apps@0.4.0/app-with-deps"
DASHBOARD_BRAND_PREFIX = "Red Hat Lightspeed —"

CSS_PLACEHOLDER = "<!-- INSIGHTS_DASHBOARD_CSS -->"
PATTERNFLY_CSS_PLACEHOLDER = "<!-- INSIGHTS_PATTERNFLY_CSS -->"
HEADER_PLACEHOLDER = "<!-- INSIGHTS_DASHBOARD_HEADER -->"
ALERT_PLACEHOLDER = "<!-- INSIGHTS_DASHBOARD_ALERT -->"
PAGINATION_PLACEHOLDER = "<!-- INSIGHTS_DASHBOARD_PAGINATION -->"
JS_PLACEHOLDER = "<!-- INSIGHTS_DASHBOARD_JS -->"

DASHBOARD_ALERT_HTML = '<div id="alert" class="alert-danger hidden"></div>'
DASHBOARD_PAGINATION_HTML = (
    '<div class="pagination hidden" id="pagination">\n'
    '                <span id="page-info"></span>\n'
    '                <div id="page-buttons" class="page-buttons"></div>\n'
    "            </div>"
)


def get_icon_data_uri() -> str:
    """Load the package icon as a base64 data URI for dashboard branding."""
    icon_data = resources.files("insights_mcp.assets").joinpath("icon.png").read_bytes()
    icon_b64 = base64.b64encode(icon_data).decode("utf-8")
    return f"data:image/png;base64,{icon_b64}"


def load_package_text(package: str, *parts: str) -> str:
    """Load a UTF-8 text file from an installed package.

    Args:
        package: Importable package name (e.g. ``insights_mcp``).
        parts: Path components within the package.

    Returns:
        File contents as a string.

    Raises:
        FileNotFoundError: If the asset is not present in the package.
    """
    return resources.files(package).joinpath(*parts).read_text(encoding="utf-8")


def load_package_text_with_fallback(
    package: str,
    parts: tuple[str, ...],
    fallback_dir: Path,
) -> str:
    """Load package text with a filesystem fallback for editable installs.

    Args:
        package: Importable package name.
        parts: Path components within the package.
        fallback_dir: Directory used when the package resource is unavailable.

    Returns:
        File contents as a string.
    """
    try:
        return load_package_text(package, *parts)
    except (FileNotFoundError, ModuleNotFoundError, AttributeError, TypeError):
        return fallback_dir.joinpath(*parts).read_text(encoding="utf-8")


def _build_header_html(dashboard_title: str) -> str:
    return (
        f'<img src="{get_icon_data_uri()}" alt="Red Hat" class="header-logo">{DASHBOARD_BRAND_PREFIX} {dashboard_title}'
    )


def _build_patternfly_link() -> str:
    return f'<link rel="stylesheet" href="{PATTERNFLY_CSS_URL}">'


def _build_common_js_block() -> str:
    common_js = load_package_text("insights_mcp", "assets/dashboard_common.js")
    common_js = common_js.replace("__INSIGHTS_MCP_APPS_SDK_URL__", MCP_APPS_SDK_URL)
    return f"<script>\n{common_js}\n</script>"


def compose_dashboard_html(
    html: str,
    *,
    dashboard_title: str,
    base_css_package: str = "insights_mcp",
    base_css_name: str = "assets/dashboard_base.css",
    extra_css: str | None = None,
) -> str:
    """Inject shared assets and dashboard-specific CSS into HTML.

    Args:
        html: Dashboard HTML containing the required placeholders.
        dashboard_title: Suffix shown in the dashboard header after the brand prefix.
        base_css_package: Package that holds the shared base stylesheet.
        base_css_name: Path to the shared base stylesheet within the package.
        extra_css: Optional dashboard-specific CSS injected after the base styles.

    Returns:
        HTML with shared CSS, JS, header, and fragment placeholders resolved.

    Raises:
        ValueError: If ``html`` is missing a required placeholder.
    """
    required_placeholders = (
        PATTERNFLY_CSS_PLACEHOLDER,
        CSS_PLACEHOLDER,
        HEADER_PLACEHOLDER,
        ALERT_PLACEHOLDER,
        PAGINATION_PLACEHOLDER,
        JS_PLACEHOLDER,
    )
    for placeholder in required_placeholders:
        if placeholder not in html:
            raise ValueError(f"dashboard HTML missing placeholder: {placeholder!r}")

    base_css = load_package_text(base_css_package, base_css_name)
    style_blocks = [f"<style>\n{base_css}\n</style>"]
    if extra_css:
        style_blocks.append(f"<style>\n{extra_css}\n</style>")

    composed = html
    composed = composed.replace(PATTERNFLY_CSS_PLACEHOLDER, _build_patternfly_link(), 1)
    composed = composed.replace(CSS_PLACEHOLDER, "\n".join(style_blocks), 1)
    composed = composed.replace(HEADER_PLACEHOLDER, _build_header_html(dashboard_title), 1)
    composed = composed.replace(ALERT_PLACEHOLDER, DASHBOARD_ALERT_HTML, 1)
    composed = composed.replace(PAGINATION_PLACEHOLDER, DASHBOARD_PAGINATION_HTML, 1)
    composed = composed.replace(JS_PLACEHOLDER, _build_common_js_block(), 1)
    return composed


def load_dashboard_html(
    package: str,
    html_filename: str,
    extra_css_filename: str,
    fallback_dir: Path,
    *,
    dashboard_title: str,
) -> str:
    """Load a dashboard HTML template and compose it with shared assets.

    Args:
        package: Toolset package name (e.g. ``inventory_mcp``).
        html_filename: Dashboard HTML filename within the package.
        extra_css_filename: Dashboard-specific CSS filename within the package.
        fallback_dir: Directory used when package resources are unavailable.
        dashboard_title: Suffix shown in the dashboard header after the brand prefix.

    Returns:
        Composed dashboard HTML ready to serve as an MCP App resource.
    """
    html = load_package_text_with_fallback(package, (html_filename,), fallback_dir)
    extra_css = load_package_text_with_fallback(package, (extra_css_filename,), fallback_dir)
    return compose_dashboard_html(html, dashboard_title=dashboard_title, extra_css=extra_css)
