"""Content quality tests for agent skills."""

from __future__ import annotations

import pytest

from tests.skills.content import (
    load_registered_tools,
    placeholder_errors,
    structure_errors,
    tool_reference_errors,
)
from tests.skills.discovery import Skill, discover_skills

SKILLS = discover_skills()
REGISTERED_TOOLS = load_registered_tools()


def _skill_id(skill: Skill) -> str:
    """Parametrize test IDs by skill directory name."""
    return skill.directory_name


def _error_report(skill: Skill, errors: list[str]) -> str:
    """Render content check errors with the SKILL.md path for context."""
    return "\n".join(f"{skill.path}: {error}" for error in errors)


def test_registered_tools_catalog_is_loaded() -> None:
    """Guard against silent toolsets.md parsing breakage with known entries."""
    assert "vulnerability" in REGISTERED_TOOLS.toolset_names
    assert "image-builder" in REGISTERED_TOOLS.toolset_names
    assert "vulnerability_get_cves" in REGISTERED_TOOLS.tool_names
    assert "image-builder__get_blueprints" in REGISTERED_TOOLS.tool_names


@pytest.mark.parametrize("skill", SKILLS, ids=_skill_id)
def test_no_placeholder_text(skill: Skill) -> None:
    """The description and body must not contain leftover placeholder markers."""
    assert not placeholder_errors(skill), _error_report(skill, placeholder_errors(skill))


@pytest.mark.parametrize("skill", SKILLS, ids=_skill_id)
def test_tool_references_are_registered(skill: Skill) -> None:
    """Backticked tool names must match tools registered in toolsets.md."""
    errors = tool_reference_errors(skill, REGISTERED_TOOLS)
    assert not errors, _error_report(skill, errors)


@pytest.mark.parametrize("skill", SKILLS, ids=_skill_id)
def test_body_has_section_headings(skill: Skill) -> None:
    """The body must contain at least one Markdown section heading."""
    assert not structure_errors(skill), _error_report(skill, structure_errors(skill))
