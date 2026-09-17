"""Tests for dashboard UI composition utilities."""

import importlib
import re

import pytest

from insights_mcp.dashboard_ui import (
    compose_dashboard_html,
    get_icon_img_tag,
    load_dashboard_html,
)

_TEMPLATE = (
    "<style>/* __DASHBOARD_BASE_CSS__ */\n/* __DASHBOARD_EXTRA_CSS__ */</style>"
    "<script>/* __DASHBOARD_COMMON_JS__ */</script>"
    "<span><!-- __DASHBOARD_ICON__ -->Title</span>"
)


def test_compose_replaces_all_placeholders() -> None:
    """Verify all four placeholders are replaced in a single pass."""
    result = compose_dashboard_html(
        _TEMPLATE,
        base_css="body { color: red; }",
        extra_css=".custom { margin: 0; }",
        common_js="function test() {}",
    )
    assert "body { color: red; }" in result
    assert ".custom { margin: 0; }" in result
    assert "function test() {}" in result
    assert '<img src="data:image/png;base64,' in result
    for placeholder in (
        "__DASHBOARD_BASE_CSS__",
        "__DASHBOARD_EXTRA_CSS__",
        "__DASHBOARD_COMMON_JS__",
        "__DASHBOARD_ICON__",
    ):
        assert placeholder not in result


def test_get_icon_img_tag_returns_img_element() -> None:
    """Verify get_icon_img_tag returns a valid img tag."""
    tag = get_icon_img_tag()
    assert tag.startswith('<img src="data:image/png;base64,')
    assert 'alt="Red Hat"' in tag
    assert tag.endswith('">')


@pytest.mark.parametrize(
    ("package", "template", "css", "marker"),
    [
        ("vulnerability_mcp", "cve_dashboard.html", "cve_dashboard.css", ".cve-row"),
        ("inventory_mcp", "inventory_dashboard.html", "inventory_dashboard.css", ".host-row"),
    ],
    ids=["cve", "inventory"],
)
def test_load_dashboard_html_produces_complete_html(package: str, template: str, css: str, marker: str) -> None:
    """Verify dashboard composition replaces all placeholders and includes expected content."""
    html = load_dashboard_html(package, template, css)
    assert "<!DOCTYPE html>" in html
    for placeholder in (
        "__DASHBOARD_BASE_CSS__",
        "__DASHBOARD_EXTRA_CSS__",
        "__DASHBOARD_COMMON_JS__",
        "__DASHBOARD_ICON__",
    ):
        assert placeholder not in html
    assert "function callTool" in html
    assert marker in html
    assert '<img src="data:image/png;base64,' in html


@pytest.mark.parametrize(
    ("module_path", "attr", "package", "template", "css"),
    [
        (
            "vulnerability_mcp.server",
            "EMBEDDED_CVE_DASHBOARD_HTML",
            "vulnerability_mcp",
            "cve_dashboard.html",
            "cve_dashboard.css",
        ),
        (
            "inventory_mcp.server",
            "EMBEDDED_INVENTORY_DASHBOARD_HTML",
            "inventory_mcp",
            "inventory_dashboard.html",
            "inventory_dashboard.css",
        ),
    ],
    ids=["cve", "inventory"],
)
def test_server_embedded_html_matches_load(module_path: str, attr: str, package: str, template: str, css: str) -> None:
    """Server module-level constants must match what load_dashboard_html produces."""
    module = importlib.import_module(module_path)
    expected = load_dashboard_html(package, template, css)
    assert getattr(module, attr) == expected


# Theme colors that must only appear inside CSS custom property definitions,
# never in inline style attributes or JS-generated HTML.
_THEME_COLORS = {"#4d4d4d", "#a3a3a3", "#292929", "#e0e0e0", "#333333", "#1a1a1a", "#2a2a2a"}

_STYLE_ATTR_RE = re.compile(r'style="([^"]*)"')


@pytest.mark.parametrize(
    ("package", "template", "css"),
    [
        ("vulnerability_mcp", "cve_dashboard.html", "cve_dashboard.css"),
        ("inventory_mcp", "inventory_dashboard.html", "inventory_dashboard.css"),
    ],
    ids=["cve", "inventory"],
)
def test_no_theme_colors_in_inline_styles(package: str, template: str, css: str) -> None:
    """Theme-dependent colors must use CSS variables, not hardcoded hex in inline styles."""
    html = load_dashboard_html(package, template, css)
    violations = []
    for match in _STYLE_ATTR_RE.finditer(html):
        style_value = match.group(1).lower()
        for color in _THEME_COLORS:
            if color in style_value:
                violations.append(f'{color} found in: style="{style_value}"')
    assert not violations, "Hardcoded theme colors in inline styles:\n" + "\n".join(violations)
