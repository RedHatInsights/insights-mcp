#!/usr/bin/env python3
"""Validate the agent skills under .agents/skills/.

Runs the format validation (agentskills.io specification) and the content
quality checks for every discovered skill. Used by the ``skill-validator``
pre-commit hook and runnable directly:

    uv run python scripts/validate_skills.py [skills-directory]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# The validators live under tests/ (imported as tests.skills). Keep this
# script runnable directly without requiring callers to configure PYTHONPATH.
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from tests.skills.content import check_content, load_registered_tools  # noqa: E402
from tests.skills.discovery import SKILLS_DIRECTORY, Skill, discover_skills  # noqa: E402
from tests.skills.validator import validate_format  # noqa: E402


def validate_all_skills(skills_directory: Path) -> tuple[list[Skill], dict[str, list[str]]]:
    """Validate all skills under *skills_directory*.

    Returns:
        The discovered skills and a mapping of SKILL.md path to error lists.
    """
    skills = discover_skills(skills_directory)
    registered_tools = load_registered_tools()
    errors_by_skill = {}
    for skill in skills:
        errors = validate_format(skill)
        errors.extend(check_content(skill, registered_tools))
        if errors:
            errors_by_skill[str(skill.path)] = errors
    return skills, errors_by_skill


def main() -> int:
    """Validate all skills and print a report; return 0 when all pass."""
    parser = argparse.ArgumentParser(description="Validate agent skills (format and content checks).")
    parser.add_argument(
        "skills_directory",
        type=Path,
        nargs="?",
        default=SKILLS_DIRECTORY,
        help="Directory containing skill subdirectories (default: .agents/skills)",
    )
    args = parser.parse_args()

    skills, errors_by_skill = validate_all_skills(args.skills_directory)
    if not skills:
        print(f"No skills found under {args.skills_directory}", file=sys.stderr)
        return 1

    for skill_path, errors in errors_by_skill.items():
        for error in errors:
            print(f"{skill_path}: {error}", file=sys.stderr)
    if errors_by_skill:
        print(f"{len(skills)} skill(s) checked, validation failed", file=sys.stderr)
        return 1
    print(f"{len(skills)} skill(s) checked, all valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
