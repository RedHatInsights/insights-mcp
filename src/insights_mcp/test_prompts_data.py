"""Shared data structures for toolset test prompt registries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

PromptEntry = str | tuple[str, tuple[str, ...], str]


@dataclass(frozen=True)
class _PromptRecord:
    prompt_id: str
    text: str
    expected_tools: tuple[str, ...] | None = None
    description: str | None = None


class PromptRegistry:
    """Registry of test prompts: plain strings or (text, expected_tools, description) tuples."""

    def __init__(self, **entries: PromptEntry) -> None:
        if not entries:
            raise ValueError("PromptRegistry requires at least one prompt entry")
        self._records: tuple[_PromptRecord, ...] = tuple(
            self._parse_entry(prompt_id, value) for prompt_id, value in entries.items()
        )
        self._by_id = {record.prompt_id: record for record in self._records}

    @staticmethod
    def _parse_entry(prompt_id: str, value: PromptEntry) -> _PromptRecord:
        if isinstance(value, str):
            return _PromptRecord(prompt_id=prompt_id, text=value)
        if (
            isinstance(value, tuple)
            and len(value) == 3
            and isinstance(value[0], str)
            and isinstance(value[1], tuple)
            and all(isinstance(tool, str) for tool in value[1])
            and isinstance(value[2], str)
        ):
            return _PromptRecord(
                prompt_id=prompt_id,
                text=value[0],
                expected_tools=value[1],
                description=value[2],
            )
        raise ValueError(
            f"invalid prompt entry for {prompt_id!r}: "
            f"want str or (str, tuple[str, ...], str), got {type(value).__name__}"
        )

    def __getitem__(self, prompt_id: str) -> str:
        return self._by_id[prompt_id].text

    def __getattr__(self, name: str) -> str:
        if name.startswith("_") or name not in self._by_id:
            raise AttributeError(name)
        return self._by_id[name].text

    def tool_usage_scenarios(self) -> list[dict[str, Any]]:
        """Entries with expected_tools, formatted for pytest parametrization."""
        return [
            {
                "prompt": record.text,
                "expected_tools": list(record.expected_tools),
                "description": record.description,
            }
            for record in self._records
            if record.expected_tools is not None
        ]


def collect_markdown_prompts(registry: PromptRegistry) -> list[str]:
    """Return deduplicated prompt texts in registry declaration order."""
    texts: list[str] = []
    seen: set[str] = set()
    for record in registry._records:
        if record.text not in seen:
            texts.append(record.text)
            seen.add(record.text)
    return texts
