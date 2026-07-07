"""Tests for shared dashboard UI CSS composition."""

import re
from pathlib import Path

import pytest

from insights_mcp.dashboard_ui import (
    CSS_PLACEHOLDER,
    HEADER_PLACEHOLDER,
    JS_PLACEHOLDER,
    MCP_APPS_SDK_URL,
    PATTERNFLY_CSS_URL,
    compose_dashboard_html,
    load_dashboard_html,
)
from inventory_mcp.server import EMBEDDED_INVENTORY_DASHBOARD_HTML, _load_inventory_dashboard_html
from vulnerability_mcp.server import EMBEDDED_CVE_DASHBOARD_HTML, _load_cve_dashboard_html

INVENTORY_DIR = Path(__file__).resolve().parents[1] / "src" / "inventory_mcp"
VULNERABILITY_DIR = Path(__file__).resolve().parents[1] / "src" / "vulnerability_mcp"


def _minimal_dashboard_html() -> str:
    """Return a dashboard HTML template containing all compose placeholders."""
    return (
        "<head>"
        "<!-- INSIGHTS_PATTERNFLY_CSS -->"
        f"{CSS_PLACEHOLDER}"
        "</head><body>"
        f"<span>{HEADER_PLACEHOLDER}</span>"
        "<!-- INSIGHTS_DASHBOARD_ALERT -->"
        "<!-- INSIGHTS_DASHBOARD_PAGINATION -->"
        f"{JS_PLACEHOLDER}"
        "</body>"
    )


def test_compose_dashboard_html_injects_base_and_extra_css() -> None:
    """Base and toolset-specific CSS are injected at the CSS placeholder."""
    html = _minimal_dashboard_html()
    composed = compose_dashboard_html(html, dashboard_title="Test", extra_css=".toolset-specific { color: red; }")

    assert CSS_PLACEHOLDER not in composed
    assert "<style>" in composed
    assert "--bg-primary:" in composed
    assert ".toolset-specific { color: red; }" in composed


def test_compose_dashboard_html_injects_shared_assets() -> None:
    """Compose replaces header, alert, pagination, PatternFly, and common JS placeholders."""
    composed = compose_dashboard_html(_minimal_dashboard_html(), dashboard_title="Inventory")

    assert PATTERNFLY_CSS_URL in composed
    assert MCP_APPS_SDK_URL in composed
    assert 'class="header-logo"' in composed
    assert "Red Hat Lightspeed — Inventory" in composed
    assert 'id="alert"' in composed
    assert 'id="pagination"' in composed
    assert "window.InsightsDashboard" in composed
    assert "renderCveDetailHtml" in composed
    assert "data:image/png;base64," in composed
    assert composed.count('class="header-logo"') == 1


def test_compose_dashboard_html_raises_without_placeholder() -> None:
    """Missing required placeholders raise ValueError."""
    with pytest.raises(ValueError, match="missing placeholder"):
        compose_dashboard_html("<html></html>", dashboard_title="Test")


def test_load_dashboard_html_from_toolset_package() -> None:
    """Inventory dashboard HTML loads shared assets and drops legacy row CSS."""
    composed = load_dashboard_html(
        "inventory_mcp",
        "inventory_dashboard.html",
        "inventory_dashboard.css",
        INVENTORY_DIR,
        dashboard_title="Inventory",
    )

    assert CSS_PLACEHOLDER not in composed
    assert ".base-row {" in composed
    assert ".filter-btn {" in composed
    assert ".host-row {" not in composed
    assert "window.InsightsDashboard" in composed


def test_embedded_inventory_dashboard_contains_shared_styles() -> None:
    """Embedded inventory dashboard includes shared CSS utilities and injected header logo."""
    assert "--bg-primary:" in EMBEDDED_INVENTORY_DASHBOARD_HTML
    assert ".search-bar {" in EMBEDDED_INVENTORY_DASHBOARD_HTML
    assert ".filter-btn {" in EMBEDDED_INVENTORY_DASHBOARD_HTML
    assert ".base-row {" in EMBEDDED_INVENTORY_DASHBOARD_HTML
    assert ".btn-compact {" in EMBEDDED_INVENTORY_DASHBOARD_HTML
    assert ".row-header {" in EMBEDDED_INVENTORY_DASHBOARD_HTML
    assert ".host-row {" not in EMBEDDED_INVENTORY_DASHBOARD_HTML
    assert 'class="header-logo"' in EMBEDDED_INVENTORY_DASHBOARD_HTML
    assert CSS_PLACEHOLDER not in EMBEDDED_INVENTORY_DASHBOARD_HTML


def test_embedded_cve_dashboard_contains_shared_styles() -> None:
    """Embedded CVE dashboard includes shared CSS, JS helpers, and no legacy row CSS."""
    assert "--bg-primary:" in EMBEDDED_CVE_DASHBOARD_HTML
    assert ".search-bar {" in EMBEDDED_CVE_DASHBOARD_HTML
    assert ".filter-btn {" in EMBEDDED_CVE_DASHBOARD_HTML
    assert ".base-row {" in EMBEDDED_CVE_DASHBOARD_HTML
    assert ".cve-row {" not in EMBEDDED_CVE_DASHBOARD_HTML
    assert "renderCveDetailHtml" in EMBEDDED_CVE_DASHBOARD_HTML
    assert CSS_PLACEHOLDER not in EMBEDDED_CVE_DASHBOARD_HTML


def test_inventory_dashboard_uses_unified_severity_classes() -> None:
    """Inventory dashboard uses shared severity-* classes instead of legacy sev-* names."""
    assert not re.search(r"sev-(critical|important|moderate|low)", EMBEDDED_INVENTORY_DASHBOARD_HTML)
    assert "severity-critical" in EMBEDDED_INVENTORY_DASHBOARD_HTML


def test_dashboard_templates_do_not_embed_inline_logo() -> None:
    """Raw dashboard templates delegate logo injection to the header placeholder."""
    inventory_template = (INVENTORY_DIR / "inventory_dashboard.html").read_text(encoding="utf-8")
    cve_template = (VULNERABILITY_DIR / "cve_dashboard.html").read_text(encoding="utf-8")

    assert "data:image/png;base64," not in inventory_template
    assert "data:image/png;base64," not in cve_template
    assert HEADER_PLACEHOLDER in inventory_template
    assert HEADER_PLACEHOLDER in cve_template


def test_inventory_and_cve_loaders_match_embedded_constants() -> None:
    """Loader functions produce the same HTML as module-level embedded constants."""
    assert _load_inventory_dashboard_html() == EMBEDDED_INVENTORY_DASHBOARD_HTML
    assert _load_cve_dashboard_html() == EMBEDDED_CVE_DASHBOARD_HTML
