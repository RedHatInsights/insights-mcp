"""Format tests for agent skills per https://agentskills.io/specification."""

from __future__ import annotations

import pytest

from tests.skills.discovery import Skill, discover_skills
from tests.skills.validator import (
    body_line_errors,
    description_errors,
    frontmatter_errors,
    name_errors,
    optional_field_errors,
    reference_errors,
)

SKILLS = discover_skills()


def _skill_id(skill: Skill) -> str:
    """Parametrize test IDs by skill directory name."""
    return skill.directory_name


def _error_report(skill: Skill, errors: list[str]) -> str:
    """Render validator errors with the SKILL.md path for context."""
    return "\n".join(f"{skill.path}: {error}" for error in errors)


def test_skills_are_discoverable() -> None:
    """Guard against silent discovery breakage: at least one skill must exist."""
    assert SKILLS, "no skills discovered under .agents/skills/"


@pytest.mark.parametrize("skill", SKILLS, ids=_skill_id)
def test_frontmatter_parses(skill: Skill) -> None:
    """SKILL.md must start with a YAML frontmatter mapping."""
    assert not frontmatter_errors(skill), _error_report(skill, frontmatter_errors(skill))


@pytest.mark.parametrize("skill", SKILLS, ids=_skill_id)
def test_name_is_valid(skill: Skill) -> None:
    """name is required, at most 64 characters of lowercase letters, numbers, and single hyphens,
    and must match the skill directory name."""
    assert not name_errors(skill), _error_report(skill, name_errors(skill))


@pytest.mark.parametrize("skill", SKILLS, ids=_skill_id)
def test_description_is_valid(skill: Skill) -> None:
    """description is required, non-empty, and at most 1024 characters."""
    assert not description_errors(skill), _error_report(skill, description_errors(skill))


@pytest.mark.parametrize("skill", SKILLS, ids=_skill_id)
def test_optional_fields_are_valid(skill: Skill) -> None:
    """Optional frontmatter fields must use the types required by the spec."""
    assert not optional_field_errors(skill), _error_report(skill, optional_field_errors(skill))


@pytest.mark.parametrize("skill", SKILLS, ids=_skill_id)
def test_body_is_under_500_lines(skill: Skill) -> None:
    """The Markdown body must stay below 500 lines."""
    assert not body_line_errors(skill), _error_report(skill, body_line_errors(skill))


@pytest.mark.parametrize("skill", SKILLS, ids=_skill_id)
def test_relative_references_resolve(skill: Skill) -> None:
    """Relative file references must resolve inside the skill directory."""
    assert not reference_errors(skill), _error_report(skill, reference_errors(skill))
