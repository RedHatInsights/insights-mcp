"""Unit tests for test prompt registry helpers."""

import pytest
from mcp_llm_eval.data import (
    PromptWithTools,
    TestScenario,
    TestScenarioRegistry,
    collect_markdown_prompts,
    format_template_for_markdown,
)

from tests.llm_prompt_catalog import TOOLSET_PROMPT_MODULES, load_registry


def test_prompt_with_tools_and_templates() -> None:
    registry = TestScenarioRegistry(
        simple=TestScenario(
            turns=(
                PromptWithTools(
                    prompt="List hosts",
                    expected_tools=("inventory__list_hosts",),
                ),
            ),
        ),
        multi=TestScenario(
            turns=(
                PromptWithTools(
                    prompt="First turn",
                    expected_tools=("image-builder__get_blueprints",),
                ),
                PromptWithTools(
                    prompt="Second turn",
                    expected_tools=("image-builder__get_blueprints",),
                ),
            ),
        ),
        templated=TestScenario(
            turns=(
                PromptWithTools(
                    prompt="CVE {cve_id} on {system_id}",
                    expected_tools=("vulnerability__get_cve",),
                ),
            ),
        ),
    )
    scenarios = registry.iter_test_scenarios("vulnerability")
    assert len(scenarios) == 3
    templated = next(s for s in scenarios if s.prompt_id == "templated")
    assert templated.required_keys == frozenset({"cve_id", "system_id"})
    assert templated.format_prompts({"cve_id": "CVE-1", "system_id": "uuid"}) == ("CVE CVE-1 on uuid",)


def test_collect_markdown_uses_examples() -> None:
    registry = TestScenarioRegistry(
        cve_systems=TestScenario(
            turns=(
                PromptWithTools(
                    prompt="Affected by {cve_id}",
                    expected_tools=("vulnerability__get_cve",),
                ),
            ),
        ),
    )
    examples = {"cve_id": "CVE-1"}
    prompts = collect_markdown_prompts(registry, examples)
    assert prompts == [format_template_for_markdown("Affected by {cve_id}", examples)]


def test_collect_markdown_prompts_deduplicates() -> None:
    registry = TestScenarioRegistry(
        first=TestScenario(
            turns=(
                PromptWithTools(
                    prompt="Same text",
                    expected_tools=("svc__a",),
                ),
            ),
        ),
        second=TestScenario(
            turns=(
                PromptWithTools(
                    prompt="Same text",
                    expected_tools=("svc__b",),
                ),
            ),
        ),
        third=TestScenario(
            turns=(
                PromptWithTools(
                    prompt="Other",
                    expected_tools=("svc__c",),
                ),
            ),
        ),
    )
    assert collect_markdown_prompts(registry, {}) == ["Same text", "Other"]


def test_turns_for_multi_turn() -> None:
    registry = TestScenarioRegistry(
        paging=TestScenario(
            turns=(
                PromptWithTools(
                    prompt="Page one",
                    expected_tools=("image-builder__get_blueprints",),
                ),
                PromptWithTools(
                    prompt="Page two",
                    expected_tools=("image-builder__get_blueprints",),
                ),
            ),
        ),
    )
    assert registry.turns_for("paging") == ("Page one", "Page two")


def test_registry_rejects_entry_without_tools() -> None:
    with pytest.raises(ValueError, match="TestScenario must contain at least one expected tool"):
        TestScenarioRegistry(
            empty_tools=TestScenario(
                turns=(
                    PromptWithTools(
                        prompt="prompt",
                        expected_tools=(),
                    ),
                ),
            ),
        )


def test_registry_requires_entries() -> None:
    with pytest.raises(ValueError, match="at least one"):
        TestScenarioRegistry()


@pytest.mark.parametrize("toolset,module_name", TOOLSET_PROMPT_MODULES)
def test_all_scenarios_declare_expected_tools(toolset: str, module_name: str) -> None:
    registry = load_registry(module_name)
    for scenario in registry.iter_test_scenarios(toolset):
        assert any(turn.expected_tools for turn in scenario.turns)
