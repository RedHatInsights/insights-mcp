"""Tests for shared dashboard UI CSS composition."""

import re
from pathlib import Path

import pytest

from insights_mcp.dashboard_ui import CSS_PLACEHOLDER, compose_dashboard_html, load_dashboard_html
from inventory_mcp.server import EMBEDDED_INVENTORY_DASHBOARD_HTML, _load_inventory_dashboard_html
from vulnerability_mcp.server import EMBEDDED_CVE_DASHBOARD_HTML, _load_cve_dashboard_html

INVENTORY_DIR = Path(__file__).resolve().parents[1] / "src" / "inventory_mcp"
VULNERABILITY_DIR = Path(__file__).resolve().parents[1] / "src" / "vulnerability_mcp"


def test_compose_dashboard_html_injects_base_and_extra_css() -> None:
    html = f"<head>{CSS_PLACEHOLDER}</head>"
    composed = compose_dashboard_html(html, extra_css=".toolset-specific { color: red; }")

    assert CSS_PLACEHOLDER not in composed
    assert "<style>" in composed
    assert "--bg-primary:" in composed
    assert ".toolset-specific { color: red; }" in composed


def test_compose_dashboard_html_raises_without_placeholder() -> None:
    with pytest.raises(ValueError, match="missing CSS placeholder"):
        compose_dashboard_html("<html></html>")


def test_load_dashboard_html_from_toolset_package() -> None:
    composed = load_dashboard_html(
        "inventory_mcp",
        "inventory_dashboard.html",
        "inventory_dashboard.css",
        INVENTORY_DIR,
    )

    assert CSS_PLACEHOLDER not in composed
    assert ".host-row {" in composed
    assert ".filter-btn {" in composed


def test_embedded_inventory_dashboard_contains_shared_styles() -> None:
    assert "--bg-primary:" in EMBEDDED_INVENTORY_DASHBOARD_HTML
    assert ".search-bar {" in EMBEDDED_INVENTORY_DASHBOARD_HTML
    assert ".filter-btn {" in EMBEDDED_INVENTORY_DASHBOARD_HTML
    assert ".host-row {" in EMBEDDED_INVENTORY_DASHBOARD_HTML
    assert CSS_PLACEHOLDER not in EMBEDDED_INVENTORY_DASHBOARD_HTML


def test_embedded_cve_dashboard_contains_shared_styles() -> None:
    assert "--bg-primary:" in EMBEDDED_CVE_DASHBOARD_HTML
    assert ".search-bar {" in EMBEDDED_CVE_DASHBOARD_HTML
    assert ".filter-btn {" in EMBEDDED_CVE_DASHBOARD_HTML
    assert ".cve-row {" in EMBEDDED_CVE_DASHBOARD_HTML
    assert CSS_PLACEHOLDER not in EMBEDDED_CVE_DASHBOARD_HTML


def test_inventory_dashboard_uses_unified_severity_classes() -> None:
    assert not re.search(r"sev-(critical|important|moderate|low)", EMBEDDED_INVENTORY_DASHBOARD_HTML)
    assert "severity-critical" in EMBEDDED_INVENTORY_DASHBOARD_HTML


def test_inventory_and_cve_loaders_match_embedded_constants() -> None:
    assert _load_inventory_dashboard_html() == EMBEDDED_INVENTORY_DASHBOARD_HTML
    assert _load_cve_dashboard_html() == EMBEDDED_CVE_DASHBOARD_HTML
