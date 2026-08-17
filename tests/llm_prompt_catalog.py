"""Toolset modules that define PROMPTS registries (for validation and docs)."""

from __future__ import annotations

import importlib

from mcp_llm_eval.data import PromptRegistry

TOOLSET_PROMPT_MODULES: list[tuple[str, str]] = [
    ("image-builder", "image_builder_mcp.test_prompts"),
    ("vulnerability", "vulnerability_mcp.test_prompts"),
    ("inventory", "inventory_mcp.test_prompts"),
    ("advisor", "advisor_mcp.test_prompts"),
    ("remediations", "remediations_mcp.test_prompts"),
    ("rbac", "rbac_mcp.test_prompts"),
    ("rhsm", "rhsm_mcp.test_prompts"),
    ("content-sources", "content_sources_mcp.test_prompts"),
    ("planning", "planning_mcp.test_prompts"),
]


def load_registry(module_name: str) -> PromptRegistry:
    """Import and return a toolset PROMPTS registry."""
    module = importlib.import_module(module_name)
    prompts = getattr(module, "PROMPTS", None)
    if not isinstance(prompts, PromptRegistry):
        raise TypeError(f"{module_name}.PROMPTS must be a PromptRegistry instance")
    return prompts
