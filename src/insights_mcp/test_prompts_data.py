"""Shared data structures for toolset test prompt registries."""

from __future__ import annotations

import re
from dataclasses import dataclass
from string import Formatter
from typing import Any, Union

_PLACEHOLDER_PATTERN = re.compile(r"\{(\w+)\}")

# Doc-only examples for generated test_prompts.md (never used at test runtime).
MARKDOWN_PLACEHOLDER_EXAMPLES: dict[str, str] = {
    "cve_id": "CVE-2024-1234",
    "system_id": "12345678-1234-1234-1234-123456789abc",
    "host_id": "12345678-1234-1234-1234-123456789abc",
    "hostname": "web-server-prod-01",
    "host_ids": ("12345678-1234-1234-1234-123456789abc, 87654321-4321-4321-4321-ba9876543210"),
    "rule_id": "network_firewall_zone_drift_enabled|ENABLE_FIREWALL_ZONE_DRIFTING_WARN",
    "workspace": "your_workspace",
    "satellite_tag": "lifecycle_environment=Prod",
    "rbac_username": "john.doe",
}


@dataclass(frozen=True)
class PromptWithTools:
    """Multi-turn prompt with required expected MCP tool names."""

    turns: tuple[str, ...]
    expected_tools: tuple[str, ...]
    description: str | None = None

    def __post_init__(self) -> None:
        if len(self.turns) < 1:
            raise ValueError("PromptWithTools.turns must contain at least one turn")
        if not self.expected_tools:
            raise ValueError("PromptWithTools.expected_tools must contain at least one tool name")


# (prompt, (tools,)) or (prompt, (tools,), description)
PromptToolsTuple = tuple[str, tuple[str, ...]] | tuple[str, tuple[str, ...], str]
PromptEntry = Union[PromptToolsTuple, PromptWithTools]


@dataclass(frozen=True)
class _PromptRecord:
    prompt_id: str
    template_turns: tuple[str, ...]
    expected_tools: tuple[str, ...]
    description: str | None = None

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

    def __init__(self, **entries: PromptEntry) -> None:
        if not entries:
            raise ValueError("PromptRegistry requires at least one prompt entry")
        self._records: tuple[_PromptRecord, ...] = tuple(
            self._parse_entry(prompt_id, value) for prompt_id, value in entries.items()
        )
        self._by_id = {record.prompt_id: record for record in self._records}
        self.validate_all_have_expected_tools()

    @staticmethod
    def _parse_entry(prompt_id: str, value: PromptEntry) -> _PromptRecord:
        if isinstance(value, PromptWithTools):
            return _PromptRecord(
                prompt_id=prompt_id,
                template_turns=value.turns,
                expected_tools=value.expected_tools,
                description=value.description,
            )
        if (
            isinstance(value, tuple)
            and len(value) == 2
            and isinstance(value[0], str)
            and isinstance(value[1], tuple)
            and all(isinstance(tool, str) for tool in value[1])
        ):
            if not value[1]:
                raise ValueError(f"prompt entry for {prompt_id!r}: expected_tools must be non-empty")
            return _PromptRecord(
                prompt_id=prompt_id,
                template_turns=(value[0],),
                expected_tools=value[1],
            )
        if (
            isinstance(value, tuple)
            and len(value) == 3
            and isinstance(value[0], str)
            and isinstance(value[1], tuple)
            and all(isinstance(tool, str) for tool in value[1])
            and isinstance(value[2], str)
        ):
            if not value[1]:
                raise ValueError(f"prompt entry for {prompt_id!r}: expected_tools must be non-empty")
            return _PromptRecord(
                prompt_id=prompt_id,
                template_turns=(value[0],),
                expected_tools=value[1],
                description=value[2],
            )
        raise ValueError(
            f"invalid prompt entry for {prompt_id!r}: "
            f"want (str, tuple[str, ...]), (str, tuple[str, ...], str), or PromptWithTools, "
            f"got {type(value).__name__}"
        )

    def validate_all_have_expected_tools(self) -> None:
        """Raise if any record lacks expected_tools (defensive; parsing should already enforce)."""
        for record in self._records:
            if not record.expected_tools:
                raise ValueError(
                    f"prompt {record.prompt_id!r} has no expected_tools; "
                    "every LLM prompt must declare at least one expected tool"
                )

    def __getitem__(self, prompt_id: str) -> str:
        return self._by_id[prompt_id].text

    def __getattr__(self, name: str) -> str:
        if name.startswith("_") or name not in self._by_id:
            raise AttributeError(name)
        return self._by_id[name].text

    def turns_for(self, prompt_id: str) -> tuple[str, ...]:
        """Return all turn templates for *prompt_id* (single- or multi-turn)."""
        return self._by_id[prompt_id].template_turns

    def tool_usage_scenarios(self) -> list[dict[str, Any]]:
        """Entries formatted for legacy pytest parametrization (image-builder easy tests)."""
        return [
            {
                "prompt": record.text,
                "expected_tools": list(record.expected_tools),
                "description": record.description or "",
            }
            for record in self._records
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


def format_template_for_markdown(template: str) -> str:
    """Render *template* with doc-only placeholder examples for markdown output."""
    formatter = Formatter()
    try:
        return formatter.vformat(template, (), _MarkdownExampleMapping())
    except KeyError:
        return template


class _MarkdownExampleMapping(dict[str, str]):
    """Mapping that supplies MARKDOWN_PLACEHOLDER_EXAMPLES for missing keys."""

    def __missing__(self, key: str) -> str:
        if key in MARKDOWN_PLACEHOLDER_EXAMPLES:
            return MARKDOWN_PLACEHOLDER_EXAMPLES[key]
        raise KeyError(key)


def collect_markdown_prompts(registry: PromptRegistry) -> list[str]:
    """Return deduplicated prompt texts in registry order (doc examples for placeholders)."""
    texts: list[str] = []
    seen: set[str] = set()
    for record in registry._records:
        for turn in record.template_turns:
            display = format_template_for_markdown(turn)
            if display not in seen:
                texts.append(display)
                seen.add(display)
    return texts
