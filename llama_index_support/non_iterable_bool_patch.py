"""
LlamaIndex MCP JSON Schema handling (historical workaround).

Previously this module monkey-patched ``TypeResolutionMixin._resolve_field_type`` because
boolean ``additionalProperties`` values were passed where a dict schema was assumed,
which raised ``TypeError: argument of type 'bool' is not iterable``.

Upstream fix: `run-llama/llama_index` PR #20082 fixed ``_create_dict_type`` and
``_is_simple_object`` in ``tool_spec_mixins.py`` so boolean ``additionalProperties``
is not forwarded to ``_resolve_field_type``. That change shipped in
``llama-index-tools-mcp`` 0.4.2+; this repo resolves 0.4.8+ (see ``uv.lock``).

``apply_llama_index_bool_patch()`` remains as a deprecated no-op so older import sites
keep working.

Optional upstream hardening: ``_resolve_field_type`` still assumes dict-shaped schemas;
a defensive ``isinstance(field_schema, bool)`` guard would only matter if another call
site passes bare booleans.
"""

from typing import Final

try:
    from llama_index.tools.mcp.tool_spec_mixins import TypeResolutionMixin
except ImportError:
    TypeResolutionMixin = None  # type: ignore[misc, assignment]


_DEPRECATED_NOOP_NOTICE: Final = (
    "apply_llama_index_bool_patch() is a no-op; use llama-index-tools-mcp>=0.4.2 (PR #20082)."
)


def apply_llama_index_bool_patch() -> bool:
    """Verify LlamaIndex MCP integration imports; patching is no longer performed.

    Returns:
        True if ``llama_index.tools.mcp`` is importable, False if Llama packages
        are not installed.
    """
    return TypeResolutionMixin is not None


if __name__ == "__main__":
    print("llama-index MCP schema patch (deprecated)")
    print("=" * 44)
    print(_DEPRECATED_NOOP_NOTICE)
    if apply_llama_index_bool_patch():
        print("llama_index.tools.mcp is importable.")
    else:
        print("llama_index.tools.mcp is not available in this environment.")
