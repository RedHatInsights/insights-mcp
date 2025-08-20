"""
Monkey patch for llama-index MCP library bug.
============================================================================

ISSUE:
------
llama-index's `McpToolSpec._resolve_field_type()` throws:
    TypeError: argument of type 'bool' is not iterable

ROOT CAUSE:
-----------
llama-index is incorrectly creating/expecting `additionalProperties: true` when processing
MCP schemas. This violates the MCP specification which expects explicit object properties.

The bug occurs when:
1. llama-index processes correct MCP schemas (like FastMCP's `anyOf` for Optional types)
2. Somewhere in its pipeline, it generates `additionalProperties: true`
3. Later processing assumes this boolean is a schema object and crashes

ACTUAL PROBLEM:
---------------
- FastMCP correctly generates: `{"anyOf": [{"type": "string"}, {"type": "null"}]}`
- MCP spec expects: explicit properties without `additionalProperties`
- llama-index incorrectly creates: `{"additionalProperties": true}` somewhere in its pipeline
- Then crashes when processing this self-created boolean value

AFFECTED CODE:
--------------
File: llama_index/tools/mcp/tool_spec_mixins.py
- Schema processing pipeline that incorrectly generates boolean `additionalProperties`
- Line 22: _resolve_field_type() - crashes on this incorrectly generated boolean

REAL-WORLD IMPACT:
------------------
This breaks MCP integration because llama-index violates the MCP specification by:
- Creating boolean `additionalProperties` that shouldn't exist in MCP schemas
- Then crashing when processing its own incorrect output

PROPER UPSTREAM FIX:
--------------------
The real fix should eliminate the source of boolean `additionalProperties` in llama-index's
MCP schema processing pipeline. However, as a defensive measure, _resolve_field_type()
should also handle boolean inputs:

    def _resolve_field_type(
        self: "McpToolSpec",
        field_schema: dict | bool,  # Update type annotation
        defs: dict,
    ) -> Any:
        # Defensive: Handle boolean field_schema (shouldn't exist in MCP schemas)
        if isinstance(field_schema, bool):
            return Any  # Fallback for incorrectly generated boolean values

        if "$ref" in field_schema:  # Now safe - field_schema is dict
            return self._resolve_reference(field_schema, defs)
        # ... rest unchanged

INVESTIGATION NEEDED:
---------------------
Find and fix where llama-index incorrectly generates `additionalProperties: true`
in its MCP schema processing pipeline.

TEMPORARY WORKAROUND:
---------------------
This file patches _resolve_field_type() as a defensive measure until the real
source of boolean `additionalProperties` is found and fixed.

TODO: Remove this file once llama-index upstream is fixed.

NOTE: This patch addresses a symptom. The real fix should prevent llama-index
from generating `additionalProperties: true` in the first place, as this
violates the MCP specification.
"""

from typing import Any

from llama_index.tools.mcp.tool_spec_mixins import TypeResolutionMixin


def apply_llama_index_bool_patch():
    """
    Apply monkey patch to fix llama-index boolean field_schema bug.

    This is a temporary workaround for the upstream bug where llama-index
    crashes when processing boolean field_schema in _resolve_field_type().

    Returns:
        bool: True if patch was applied, False if llama-index not available
    """
    try:
        # Store original method
        # pylint: disable=protected-access
        original_resolve_field_type = TypeResolutionMixin._resolve_field_type

        def _patched_resolve_field_type(self, field_schema: dict | bool, defs: dict) -> Any:
            """
            Resolve the Python type from a field schema - patched to handle boolean inputs.

            UPSTREAM BUG WORKAROUND:
            This patches the root cause where _resolve_field_type() assumes field_schema
            is always a dict, but JSON Schema allows boolean additionalProperties.

            Args:
                field_schema: JSON schema dict OR boolean (for additionalProperties)
                defs: Schema definitions dict

            Returns:
                Python type for the field
            """
            # Handle boolean field_schema (for additionalProperties: true/false)
            if isinstance(field_schema, bool):
                # JSON Schema allows boolean additionalProperties
                # Both true and false resolve to Any since we can't represent
                # "disallow additional properties" in Python's type system
                return Any

            # Call original method for dict field_schema
            return original_resolve_field_type(self, field_schema, defs)

        # Apply the patch
        # pylint: disable=protected-access
        TypeResolutionMixin._resolve_field_type = _patched_resolve_field_type

        return True

    except ImportError:
        # llama-index not installed - patch not needed
        return False


def is_patch_needed():
    """
    Check if the patch is still needed by testing the bug condition.

    Returns:
        bool: True if patch is needed, False if upstream is fixed or not available
    """
    try:
        # Create test instance
        test_instance = TypeResolutionMixin()

        try:
            # Test the exact bug: boolean field_schema crashes _resolve_field_type
            # This will crash with TypeError if bug exists
            # pylint: disable=protected-access
            test_instance._resolve_field_type(True, {})
            return False  # No crash = bug is fixed upstream
        except TypeError as e:
            return "argument of type 'bool' is not iterable" in str(e)
        except AttributeError:
            # _resolve_field_type doesn't exist, probably different llama-index version
            return False

    except ImportError:
        # llama-index not available
        return False


# Auto-apply patch when module is imported
if __name__ != "__main__" and is_patch_needed():
    apply_llama_index_bool_patch()


if __name__ == "__main__":
    # Test/debug mode
    print("llama-index Boolean field_schema Patch")
    print("=" * 45)

    if is_patch_needed():
        print("❌ Bug detected - patch needed")
        print("   _resolve_field_type() crashes on boolean input")
        if apply_llama_index_bool_patch():
            print("✅ Patch applied successfully")
        else:
            print("❌ Failed to apply patch")
    else:
        print("✅ Bug not detected - patch not needed")
        print("   Either llama-index is fixed or not available")
