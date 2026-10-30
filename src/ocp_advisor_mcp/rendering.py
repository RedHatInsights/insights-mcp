"""Render Advisor and DVO DoT.js templates using doT-js-py and PythonMonkey.

Settings and escaping follow insights-content-template-renderer. Failed fields
retain their templates and are reported in the recommendation's rendering status.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

import doT

TEMPLATE_FIELDS = ("reason", "resolution", "more_info", "details")

# Advisor's details field is prose; per-hit template data is in extra_data.
ADVISOR_TEMPLATE_FIELDS = ("reason", "resolution", "more_info")

# Match upstream's pydata variable name rather than doT's default it.
PYDATA_TEMPLATE_SETTINGS = doT.TemplateSettings()._replace(varname="pydata")


class RenderingError(Exception):
    """Raised when a DoT.js template cannot be rendered."""


def _escape_raw_text_for_js(text: str) -> str:
    """Escape template text as in insights-content-template-renderer."""
    return text.encode("unicode_escape").decode()


def _escape_new_line_inside_brackets(text: str) -> str:
    r"""Strip escaped newlines before closing template brackets (upstream CCXDEV-10314)."""
    return re.sub(r"{{(.*?)\\n}}", r"{{\1}}", text)


def _unescape_raw_text_for_python(text: str) -> str:
    """Undo the JS-side escaping of special characters in rendered text."""
    return text.encode().decode("unicode-escape")


class DotRenderer:  # pylint: disable=too-few-public-methods
    """Render DoT.js templates with cached compiled functions."""

    def __init__(self) -> None:
        self._compiled: dict[str, Any] = {}

    def _get_template_function(self, template_text: str) -> Any:
        """Compile a template, reusing cached functions."""
        cached = self._compiled.get(template_text)
        if cached is not None:
            return cached

        try:
            # Keep runtime import failures local to rendering tools.
            import pythonmonkey  # pylint: disable=import-outside-toplevel
        except Exception as exc:
            raise RenderingError(f"JavaScript runtime (pythonmonkey) unavailable: {exc}") from exc

        escaped = _escape_new_line_inside_brackets(_escape_raw_text_for_js(template_text))
        js_code = doT.template(escaped, PYDATA_TEMPLATE_SETTINGS)
        try:
            function = pythonmonkey.eval(f"({js_code})")  # pylint: disable=no-member
        except Exception as exc:
            raise RenderingError(f"Failed to compile DoT.js template: {exc}") from exc

        self._compiled[template_text] = function
        return function

    def render(self, template_text: str, data: Mapping[str, Any]) -> str:
        """Render a template with the supplied data."""
        if not template_text:
            raise RenderingError("Empty template")

        function = self._get_template_function(template_text)
        try:
            result = function(dict(data))
        except Exception as exc:
            raise RenderingError(f"Failed to execute DoT.js template: {exc}") from exc

        if not isinstance(result, str):
            raise RenderingError(f"DoT.js template returned {type(result).__name__}, expected string")
        return _unescape_raw_text_for_python(result)


_renderer = DotRenderer()


def render_template(template_text: str | None, data: Mapping[str, Any]) -> str:
    """Render a single template."""
    return _renderer.render(template_text or "", data)


def render_recommendation_fields(
    recommendation: Mapping[str, Any],
    data: Mapping[str, Any],
    fields: tuple[str, ...] = TEMPLATE_FIELDS,
) -> tuple[dict[str, str], dict[str, str]]:
    """Return rendered fields and per-field errors without modifying the recommendation.

    Missing, empty, and non-string fields are skipped.
    """
    rendered: dict[str, str] = {}
    errors: dict[str, str] = {}
    for field in fields:
        template_text = recommendation.get(field)
        if not isinstance(template_text, str) or not template_text:
            continue
        try:
            rendered[field] = render_template(template_text, data)
        except RenderingError as exc:
            errors[field] = str(exc)
    return rendered, errors


def apply_rendering_status(recommendation: dict[str, Any], errors: Mapping[str, str]) -> None:
    """Set rendering status to ``ok`` or ``failed`` with per-field errors."""
    if not errors:
        recommendation["rendering"] = {"status": "ok"}
    else:
        recommendation["rendering"] = {"status": "failed", "errors": dict(errors)}
