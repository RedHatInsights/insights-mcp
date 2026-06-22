"""Unit tests for test prompt registry helpers."""

import pytest

from insights_mcp.test_prompts_data import (
    PromptRegistry,
    PromptWithTools,
    collect_markdown_prompts,
    format_template_for_markdown,
)
from tests.llm_prompt_catalog import TOOLSET_PROMPT_MODULES, load_registry


def test_shorthand_and_prompt_with_tools() -> None:
    registry = PromptRegistry(
        simple=("List hosts", ("inventory__list_hosts",)),
        multi=PromptWithTools(
            turns=("First turn", "Second turn"),
            expected_tools=("image-builder__get_blueprints",),
        ),
        templated=(
            "CVE {cve_id} on {system_id}",
            ("vulnerability__get_cve",),
        ),
    )
    scenarios = registry.iter_test_scenarios("vulnerability")
    assert len(scenarios) == 3
    templated = next(s for s in scenarios if s.prompt_id == "templated")
    assert templated.required_keys == frozenset({"cve_id", "system_id"})
    assert templated.format_turns({"cve_id": "CVE-1", "system_id": "uuid"}) == ("CVE CVE-1 on uuid",)


def test_collect_markdown_uses_examples() -> None:
    registry = PromptRegistry(cve_systems=("Affected by {cve_id}", ("vulnerability__get_cve",)))
    prompts = collect_markdown_prompts(registry)
    assert prompts == [format_template_for_markdown("Affected by {cve_id}")]


def test_collect_markdown_prompts_deduplicates() -> None:
    registry = PromptRegistry(
        first=("Same text", ("svc__a",)),
        second=("Same text", ("svc__b",), "tool test"),
        third=("Other", ("svc__c",)),
    )
    assert collect_markdown_prompts(registry) == ["Same text", "Other"]


def test_tool_usage_scenarios() -> None:
    registry = PromptRegistry(
        example=("Hello", ("svc__tool",)),
        tool_case=("Run tool", ("svc__tool",), "uses tool"),
    )
    assert registry["example"] == "Hello"
    assert registry.example == "Hello"
    assert registry.tool_usage_scenarios() == [
        {
            "prompt": "Hello",
            "expected_tools": ["svc__tool"],
            "description": "",
        },
        {
            "prompt": "Run tool",
            "expected_tools": ["svc__tool"],
            "description": "uses tool",
        },
    ]


def test_turns_for_multi_turn() -> None:
    registry = PromptRegistry(
        paging=PromptWithTools(
            turns=("Page one", "Page two"),
            expected_tools=("image-builder__get_blueprints",),
        ),
    )
    assert registry.turns_for("paging") == ("Page one", "Page two")


def test_registry_rejects_entry_without_tools() -> None:
    with pytest.raises(ValueError, match="expected_tools must be non-empty"):
        PromptRegistry(empty_tools=("prompt", ()))


def test_registry_rejects_invalid_entry() -> None:
    with pytest.raises(ValueError, match="invalid prompt entry"):
        PromptRegistry(bad=("only", "two"))  # type: ignore[arg-type]


def test_registry_requires_entries() -> None:
    with pytest.raises(ValueError, match="at least one"):
        PromptRegistry()


@pytest.mark.parametrize("toolset,module_name", TOOLSET_PROMPT_MODULES)
def test_all_toolset_prompts_declare_expected_tools(toolset: str, module_name: str) -> None:
    registry = load_registry(module_name)
    registry.validate_all_have_expected_tools()
    for scenario in registry.iter_test_scenarios(toolset):
        assert scenario.expected_tools
