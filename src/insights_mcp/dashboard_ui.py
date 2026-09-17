"""Dashboard UI composition utilities.

Composes self-contained HTML dashboards by combining shared assets
(base CSS, common JS) with dashboard-specific templates and styles.
"""

import base64
from importlib import resources
from pathlib import Path


def _read_asset(filename: str) -> str:
    """Read a file from the insights_mcp.assets package."""
    try:
        return resources.files("insights_mcp.assets").joinpath(filename).read_text(encoding="utf-8")
    except (FileNotFoundError, ModuleNotFoundError, AttributeError, TypeError):
        return (Path(__file__).parent / "assets" / filename).read_text(encoding="utf-8")


def _read_package_file(package: str, filename: str) -> str:
    """Read a file from a specific package."""
    try:
        return resources.files(package).joinpath(filename).read_text(encoding="utf-8")
    except (FileNotFoundError, ModuleNotFoundError, AttributeError, TypeError):
        # Fallback for editable installs
        pkg_dir = Path(__file__).parent.parent / package
        return (pkg_dir / filename).read_text(encoding="utf-8")


def get_icon_img_tag() -> str:
    """Build an <img> tag with the Red Hat icon as a base64 data URI."""
    try:
        icon_data = resources.files("insights_mcp.assets").joinpath("icon.png").read_bytes()
    except (FileNotFoundError, ModuleNotFoundError, AttributeError, TypeError):
        icon_data = (Path(__file__).parent / "assets" / "icon.png").read_bytes()
    icon_b64 = base64.b64encode(icon_data).decode("utf-8")
    return (
        f'<img src="data:image/png;base64,{icon_b64}" '
        f'alt="Red Hat" style="height:16px;vertical-align:middle;margin-right:6px;">'
    )


def compose_dashboard_html(
    template: str,
    *,
    base_css: str,
    extra_css: str = "",
    common_js: str,
) -> str:
    """Replace placeholders in a dashboard HTML template with shared assets.

    Placeholders:
        /* __DASHBOARD_BASE_CSS__ */   -> base CSS content
        /* __DASHBOARD_EXTRA_CSS__ */  -> dashboard-specific CSS content
        /* __DASHBOARD_COMMON_JS__ */  -> common JS utilities
        <!-- __DASHBOARD_ICON__ -->    -> <img> tag with base64 icon
    """
    icon_tag = get_icon_img_tag()

    html = template
    html = html.replace("/* __DASHBOARD_BASE_CSS__ */", base_css)
    html = html.replace("/* __DASHBOARD_EXTRA_CSS__ */", extra_css)
    html = html.replace("/* __DASHBOARD_COMMON_JS__ */", common_js)
    html = html.replace("<!-- __DASHBOARD_ICON__ -->", icon_tag)
    return html


def load_dashboard_html(
    package: str,
    template_name: str,
    css_name: str,
) -> str:
    """Load and compose a dashboard HTML from package resources.

    Reads the template HTML and dashboard-specific CSS from *package*,
    reads shared base CSS and common JS from insights_mcp.assets,
    and composes them into a self-contained HTML string.
    """
    template = _read_package_file(package, template_name)
    extra_css = _read_package_file(package, css_name)
    base_css = _read_asset("dashboard_base.css")
    common_js = _read_asset("dashboard_common.js")

    return compose_dashboard_html(
        template,
        base_css=base_css,
        extra_css=extra_css,
        common_js=common_js,
    )
