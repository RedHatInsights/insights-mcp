"""Content quality checks for agent skills.

Checks for placeholder text, references to tools that are not registered in
``toolsets.md``, and minimal section structure. The registered tool names are
parsed from the generated ``toolsets.md`` so the checks work offline; CI
verifies that ``toolsets.md`` is current via ``make generate-docs``.

Each rule has a dedicated ``*_errors`` function so tests can assert one
criterion at a time; ``check_content`` combines them for the CLI.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from tests.skills.discovery import REPOSITORY_ROOT, Skill

#: Generated catalog of all toolsets and their tools (see ``make generate-docs``).
TOOLSETS_MARKDOWN = REPOSITORY_ROOT / "toolsets.md"

#: Tools registered directly on the root server in ``insights_mcp/server.py``.
#: They have no toolset prefix; ``get_mcp_version`` is currently the only one.
ROOT_SERVER_TOOLS = frozenset({"get_mcp_version"})

#: Placeholder markers that must be resolved before a skill is published.
_PLACEHOLDER_PATTERNS = (
    re.compile(r"\b(?:TODO|TBD|FIXME|XXX)\b"),
    re.compile(r"lorem ipsum", re.IGNORECASE),
    re.compile(r"<placeholder>", re.IGNORECASE),
)

_TOOLSET_HEADER_PATTERN = re.compile(r"^## (?P<toolset>\S+)\s*$")
_TOOL_ENTRY_PATTERN = re.compile(r"^- `(?P<tool>[a-z0-9_]+)`")
#: Lowercase tokens containing underscores, e.g. ``vulnerability_get_cves``.
_TOOL_REFERENCE_PATTERN = re.compile(r"^[a-z][a-z0-9-]*_[a-z][a-z0-9_-]*$")
_BACKTICK_PATTERN = re.compile(r"`([^`\n]+)`")
_SECTION_HEADING_PATTERN = re.compile(r"^## ", re.MULTILINE)


@dataclass(frozen=True)
class RegisteredTools:
    """Toolset and tool names parsed from toolsets.md.

    Attributes:
        toolset_names: All registered toolset names (for example ``image-builder``).
        tool_names: All prefixed tool names in both separator styles used by
            clients (``image-builder_get_blueprints`` and
            ``image-builder__get_blueprints``).
    """

    toolset_names: frozenset[str]
    tool_names: frozenset[str]


def load_registered_tools(toolsets_markdown: Path = TOOLSETS_MARKDOWN) -> RegisteredTools:
    """Parse *toolsets_markdown* into toolset names and prefixed tool names.

    Args:
        toolsets_markdown: Path of the generated toolsets.md file.

    Returns:
        The registered toolsets and their tool names.
    """
    tools_by_toolset: dict[str, set[str]] = {}
    current_toolset: str | None = None
    for line in toolsets_markdown.read_text(encoding="utf-8").splitlines():
        header = _TOOLSET_HEADER_PATTERN.match(line)
        if header:
            current_toolset = header.group("toolset")
            tools_by_toolset.setdefault(current_toolset, set())
            continue
        entry = _TOOL_ENTRY_PATTERN.match(line)
        if entry and current_toolset:
            tools_by_toolset[current_toolset].add(entry.group("tool"))

    tool_names: set[str] = set()
    for toolset, tools in tools_by_toolset.items():
        for tool in tools:
            tool_names.add(f"{toolset}_{tool}")
            tool_names.add(f"{toolset}__{tool}")
    return RegisteredTools(
        toolset_names=frozenset(tools_by_toolset),
        tool_names=frozenset(tool_names),
    )


def check_content(skill: Skill, registered_tools: RegisteredTools) -> list[str]:
    """Return all content quality violations for *skill* (empty when valid)."""
    errors = placeholder_errors(skill)
    errors.extend(tool_reference_errors(skill, registered_tools))
    errors.extend(structure_errors(skill))
    return errors


def placeholder_errors(skill: Skill) -> list[str]:
    """The description and body must not contain leftover placeholder markers."""
    errors: list[str] = []
    description = ""
    if skill.frontmatter is not None:
        description_value = skill.frontmatter.get("description")
        if isinstance(description_value, str):
            description = description_value
    text = f"{description}\n{skill.body}"
    for pattern in _PLACEHOLDER_PATTERNS:
        for match in pattern.finditer(text):
            errors.append(f"placeholder text {match.group(0)!r} must be resolved before publishing")
    return errors


def tool_reference_errors(skill: Skill, registered_tools: RegisteredTools) -> list[str]:
    """Backticked tool names must reference registered tools.

    A backticked token is treated as a tool reference when it is lowercase,
    contains an underscore, and starts with a registered toolset name (for
    example ``vulnerability_get_cves`` or ``image-builder__get_blueprints``).
    Root server tools such as ``get_mcp_version`` are always valid. Tokens
    with another prefix are ignored: they may be commands or variable names
    that merely look like tool names.
    """
    errors: list[str] = []
    for token in _BACKTICK_PATTERN.findall(skill.body):
        token = token.strip()
        if not _TOOL_REFERENCE_PATTERN.fullmatch(token):
            continue
        if token in ROOT_SERVER_TOOLS or token in registered_tools.tool_names:
            continue
        prefix = token.split("_", 1)[0]
        if prefix in registered_tools.toolset_names:
            errors.append(
                f"tool reference {token!r} is not a registered tool of the {prefix!r} toolset (see toolsets.md)"
            )
    return errors


def structure_errors(skill: Skill) -> list[str]:
    """The body must contain at least one Markdown section heading."""
    if not _SECTION_HEADING_PATTERN.search(skill.body):
        return ["body must contain at least one '## ' section heading"]
    return []
