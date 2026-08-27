"""Shared data structures for toolset test prompt registries."""

from __future__ import annotations

import re
from dataclasses import dataclass
from string import Formatter
from typing import Any

_PLACEHOLDER_PATTERN = re.compile(r"\{(\w+)\}")


@dataclass(frozen=True)
class PromptWithTools:
    """Single conversation turn with expected MCP tool calls."""

    prompt: str  # Just a template with unresolved keys
    expected_tools: tuple[str, ...] = ()
    forbidden_tools: tuple[str, ...] = ()
    expected_args: dict[str, list[dict[str, Any]]] | None = None
    turn_criteria: str | None = None

    def __post_init__(self) -> None:
        """Validate that argument expectations refer to expected tools."""
        if self.expected_args:
            unexpected_tools = set(self.expected_args) - set(self.expected_tools)
            if unexpected_tools:
                raise ValueError(
                    "PromptWithTools.expected_args contains tools not listed in expected_tools: "
                    f"{sorted(unexpected_tools)}"
                )


@dataclass(frozen=True)
class TestScenario:
    """Multi-turn test scenario with per-turn tool expectations."""

    turns: tuple[PromptWithTools, ...]
    conversation_criteria: str | None = None
    assert_no_memory_overflow: bool = False

    def __post_init__(self) -> None:
        if len(self.turns) < 1:
            raise ValueError("TestScenario.turns must contain at least one turn")
        if not any(turn.expected_tools for turn in self.turns):
            raise ValueError("TestScenario must contain at least one expected tool")


@dataclass(frozen=True)
class _ScenarioRecord:
    prompt_id: str
    turns: tuple[PromptWithTools, ...]
    conversation_criteria: str | None
    assert_no_memory_overflow: bool

    @property
    def required_keys(self) -> frozenset[str]:
        """Placeholder names required to format all prompts."""
        keys: set[str] = set()
        for turn in self.turns:
            keys.update(_PLACEHOLDER_PATTERN.findall(turn.prompt))
        return frozenset(keys)

    @classmethod
    def from_scenario(cls, prompt_id: str, value: TestScenario) -> _ScenarioRecord:
        """Create a record from a test scenario configuration entry."""
        return cls(
            prompt_id=prompt_id,
            turns=value.turns,
            conversation_criteria=value.conversation_criteria,
            assert_no_memory_overflow=value.assert_no_memory_overflow,
        )


@dataclass(frozen=True)
class PromptTestScenario:
    """One parametrized LLM test scenario (unresolved templates)."""

    prompt_id: str
    turns: tuple[PromptWithTools, ...]
    required_keys: frozenset[str]
    conversation_criteria: str | None
    assert_no_memory_overflow: bool

    def format_prompts(self, context: dict[str, str]) -> tuple[str, ...]:
        """Substitute placeholders in every turn's prompt using *context*."""
        return tuple(turn.prompt.format(**context) for turn in self.turns)

    @property
    def prompt(self) -> str:
        """Return the first turn template as the primary prompt."""
        return self.turns[0].prompt


class TestScenarioRegistry:
    """Registry of LLM test scenarios."""

    def __init__(self, **entries: TestScenario) -> None:
        if not entries:
            raise ValueError("TestScenarioRegistry requires at least one scenario entry")
        self._records: tuple[_ScenarioRecord, ...] = tuple(
            _ScenarioRecord.from_scenario(prompt_id, value) for prompt_id, value in entries.items()
        )

    def iter_test_scenarios(self) -> list[PromptTestScenario]:
        """Return unresolved scenarios for LLM tests."""
        return [
            PromptTestScenario(
                prompt_id=record.prompt_id,
                turns=record.turns,
                required_keys=record.required_keys,
                conversation_criteria=record.conversation_criteria,
                assert_no_memory_overflow=record.assert_no_memory_overflow,
            )
            for record in self._records
        ]


def format_template_for_markdown(template: str, placeholder_examples: dict[str, str]) -> str:
    """Render *template* with doc-only placeholder examples for markdown output."""
    formatter = Formatter()
    try:
        return formatter.vformat(template, (), placeholder_examples)
    except KeyError:
        return template


def collect_markdown_prompts(registry: TestScenarioRegistry, placeholder_examples: dict[str, str]) -> list[str]:
    """Return deduplicated prompt texts in registry order (doc examples for placeholders)."""
    texts: list[str] = []
    seen: set[str] = set()
    for record in registry._records:
        for turn in record.turns:
            display = format_template_for_markdown(turn.prompt, placeholder_examples)
            if display not in seen:
                texts.append(display)
                seen.add(display)
    return texts
