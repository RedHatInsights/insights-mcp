"""Unit tests for shared test prompt registry helpers."""

import pytest

from insights_mcp.test_prompts_data import PromptRegistry, collect_markdown_prompts


def test_prompt_registry_plain_and_tool_usage() -> None:
    registry = PromptRegistry(
        example="Hello",
        tool_case=("Run tool", ("svc__tool",), "uses tool"),
    )
    assert registry["example"] == "Hello"
    assert registry.example == "Hello"
    scenarios = registry.tool_usage_scenarios()
    assert scenarios == [
        {
            "prompt": "Run tool",
            "expected_tools": ["svc__tool"],
            "description": "uses tool",
        },
    ]


def test_collect_markdown_prompts_deduplicates() -> None:
    registry = PromptRegistry(
        first="Same text",
        second=("Same text", ("svc__a",), "tool test"),
        third="Other",
    )
    assert collect_markdown_prompts(registry) == ["Same text", "Other"]


def test_prompt_registry_rejects_invalid_entry() -> None:
    with pytest.raises(ValueError, match="invalid prompt entry"):
        PromptRegistry(bad=("only", "two"))  # type: ignore[arg-type]


def test_prompt_registry_requires_entries() -> None:
    with pytest.raises(ValueError, match="at least one"):
        PromptRegistry()
