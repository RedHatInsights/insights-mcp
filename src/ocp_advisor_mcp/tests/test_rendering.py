"""Test suite for the DoT.js rendering helpers."""

import sys
from typing import Any
from unittest.mock import patch

import pytest

from ocp_advisor_mcp.rendering import (
    RenderingError,
    render_recommendation_fields,
    render_template,
)


def test_render_template_substitutes_cluster_specific_values() -> None:
    """DoT.js templates render with the report details passed as context."""
    template = "Cluster {{=pydata.cluster_name}} has {{=pydata.hits}} findings."
    assert render_template(template, {"cluster_name": "prod-cluster", "hits": 3}) == (
        "Cluster prod-cluster has 3 findings."
    )


def test_render_template_without_interpolation() -> None:
    """Static template text is returned unchanged."""
    assert render_template("No placeholders here.", {}) == "No placeholders here."


def test_render_template_empty_raises() -> None:
    """Empty templates raise RenderingError instead of returning rendered text."""
    with pytest.raises(RenderingError, match="Empty template"):
        render_template("", {})


def test_render_template_runtime_unavailable_raises() -> None:
    """A missing JavaScript runtime is reported as an explicit rendering failure."""
    with patch.dict(sys.modules, {"pythonmonkey": None}):
        with pytest.raises(RenderingError, match="pythonmonkey"):
            render_template("Hello {{=pydata.name}}", {"name": "x"})


def test_render_template_iteration_over_list() -> None:
    """``{{~ list:item }}`` loops iterate lists, as used by CVE fix-version templates."""
    template = (
        "Fixed versions for higher minor versions of OpenShift are as follows:\n"
        "{{~ pydata.higher_eligible_fixed_versions:version }}\n"
        "- {{=version}}\n"
        "{{~}}"
    )
    data: dict[str, Any] = {"higher_eligible_fixed_versions": ["4.19.31", "4.20.22"]}
    rendered = render_template(template, data)
    assert "- 4.19.31" in rendered
    assert "- 4.20.22" in rendered


def test_render_template_raw_js_block() -> None:
    """Raw JavaScript ``{{ for ... { }}`` blocks render, as used by operator rule templates."""
    template = (
        "{{ for (var operator_kind in pydata.operator_settings) { }}\n"
        "Operator **{{=operator_kind}}**:\n"
        "{{~pydata.operator_settings[operator_kind]:setting}}\n"
        "- {{=setting}}\n"
        "{{~}}\n"
        "{{ } }}"
    )
    data: dict[str, Any] = {
        "operator_settings": {"openshiftcontrollermanager": ["dockerPullSecret"]}
    }
    rendered = render_template(template, data)
    assert "Operator **openshiftcontrollermanager**:" in rendered
    assert "- dockerPullSecret" in rendered


def test_render_template_platform_pydata_dialect() -> None:
    """Real Advisor rule templates (``pydata.*`` with doT conditionals) render."""
    template = (
        "{{? pydata.fixed_version }}\n"
        "upgrade your cluster to {{=pydata.fixed_version}}.\n"
        "{{??}}\n"
        "no fixed version yet\n"
        "{{?}}"
    )
    data: dict[str, Any] = {"fixed_version": "4.21.40"}
    assert "4.21.40" in render_template(template, data)

    data = {"fixed_version": ""}
    assert "no fixed version yet" in render_template(template, data)


def test_render_recommendation_fields_reports_failures() -> None:
    """Failed fields keep their unresolved template and are reported as errors."""
    recommendation = {
        "rule_id": "test.rule|TEST_KEY",
        "reason": "Reason for {{=pydata.missing_value()}}",
        "resolution": "",
        "more_info": "Static more info",
    }
    rendered, errors = render_recommendation_fields(recommendation, {})

    # more_info renders, resolution is skipped (no template), reason fails
    assert rendered == {"more_info": "Static more info"}
    assert set(errors) == {"reason"}
    # the unresolved template is preserved
    assert recommendation["reason"] == "Reason for {{=pydata.missing_value()}}"
