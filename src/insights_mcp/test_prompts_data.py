"""Shared data structures for toolset test prompt registries."""

from __future__ import annotations

import re
from dataclasses import dataclass
from string import Formatter
from typing import Any

_PLACEHOLDER_PATTERN = re.compile(r"\{(\w+)\}")


@dataclass(frozen=True)
class PromptWithTools:
    """Multi-turn prompt with at least one expected MCP tool name."""

    turns: tuple[str, ...]
    expected_tools: tuple[str, ...]
    description: str | None = None
    guardian_criteria: str | None = None
    forbidden_tools: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if len(self.turns) < 1:
            raise ValueError("PromptWithTools.turns must contain at least one turn")
        if not self.expected_tools:
            raise ValueError("PromptWithTools.expected_tools must contain at least one tool name")


@dataclass(frozen=True)
class _PromptRecord:
    prompt_id: str
    template_turns: tuple[str, ...]
    expected_tools: tuple[str, ...]
    description: str | None = None
    guardian_criteria: str | None = None
    forbidden_tools: tuple[str, ...] = ()

    @property
    def text(self) -> str:
        """First turn text (backward compatible with single-turn access)."""
        return self.template_turns[0]

    @property
    def required_keys(self) -> frozenset[str]:
        """Placeholder names required to format all turns."""
        keys: set[str] = set()
        for turn in self.template_turns:
            keys.update(_PLACEHOLDER_PATTERN.findall(turn))
        return frozenset(keys)

    @classmethod
    def from_prompt(cls, prompt_id: str, value: PromptWithTools) -> _PromptRecord:
        """Create a record from a prompt configuration entry."""
        return cls(
            prompt_id=prompt_id,
            template_turns=value.turns,
            expected_tools=value.expected_tools,
            description=value.description,
            guardian_criteria=value.guardian_criteria,
            forbidden_tools=value.forbidden_tools,
        )


@dataclass(frozen=True)
class PromptTestScenario:
    """One parametrized LLM test scenario (unresolved templates)."""

    toolset: str
    prompt_id: str
    template_turns: tuple[str, ...]
    required_keys: frozenset[str]
    expected_tools: tuple[str, ...]

    def format_turns(self, context: dict[str, str]) -> tuple[str, ...]:
        """Substitute placeholders in every turn using *context*."""
        return tuple(turn.format(**context) for turn in self.template_turns)


class PromptRegistry:
    """Registry of LLM test prompts; every entry must declare expected_tools."""

    def __init__(self, **entries: PromptWithTools) -> None:
        if not entries:
            raise ValueError("PromptRegistry requires at least one prompt entry")
        self._records: tuple[_PromptRecord, ...] = tuple(
            _PromptRecord.from_prompt(prompt_id, value) for prompt_id, value in entries.items()
        )
        self._by_id = {record.prompt_id: record for record in self._records}

    def __getitem__(self, prompt_id: str) -> str:
        return self._by_id[prompt_id].text

    def __getattr__(self, name: str) -> str:
        if name.startswith("_") or name not in self._by_id:
            raise AttributeError(name)
        return self._by_id[name].text

    def turns_for(self, prompt_id: str) -> tuple[str, ...]:
        """Return all turn templates for *prompt_id* (single- or multi-turn)."""
        return self._by_id[prompt_id].template_turns

    def tool_usage_scenarios(self, exclude: set[str] | None = None) -> list[dict[str, Any]]:
        """Entries formatted for legacy pytest parametrization (image-builder easy tests)."""
        return [
            {
                "prompt": record.text,
                "expected_tools": list(record.expected_tools),
                "description": record.description or "",
            }
            for record in self._records
            if exclude is None or record.prompt_id not in exclude
        ]

    def guardian_scenarios(self) -> list[dict[str, Any]]:
        """Entries that require LLM-judged (guardian) evaluation."""
        return [
            {
                "prompt_id": record.prompt_id,
                "prompt": record.text,
                "expected_tools": list(record.expected_tools),
                "guardian_criteria": record.guardian_criteria,
                "forbidden_tools": list(record.forbidden_tools),
            }
            for record in self._records
            if record.guardian_criteria
        ]

    def iter_test_scenarios(self, toolset: str) -> list[PromptTestScenario]:
        """Return unresolved scenarios for per-toolset LLM tests."""
        return [
            PromptTestScenario(
                toolset=toolset,
                prompt_id=record.prompt_id,
                template_turns=record.template_turns,
                required_keys=record.required_keys,
                expected_tools=record.expected_tools,
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


def collect_markdown_prompts(registry: PromptRegistry, placeholder_examples: dict[str, str]) -> list[str]:
    """Return deduplicated prompt texts in registry order (doc examples for placeholders)."""
    texts: list[str] = []
    seen: set[str] = set()
    for record in registry._records:
        for turn in record.template_turns:
            display = format_template_for_markdown(turn, placeholder_examples)
            if display not in seen:
                texts.append(display)
                seen.add(display)
    return texts
