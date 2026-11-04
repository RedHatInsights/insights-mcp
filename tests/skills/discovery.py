"""Discovery and parsing of agent skills (SKILL.md directories).

A skill is a directory under ``.agents/skills/`` containing a ``SKILL.md``
file with YAML frontmatter and a Markdown body, following the agent skills
specification (https://agentskills.io/specification).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import yaml

#: Repository root, derived from this file's location (tests/skills/).
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

#: Directory that contains one subdirectory per agent skill.
SKILLS_DIRECTORY = REPOSITORY_ROOT / ".agents" / "skills"

#: File name that every skill directory must contain.
SKILL_FILE_NAME = "SKILL.md"


@dataclass(frozen=True)
class Skill:
    """One parsed SKILL.md file.

    Attributes:
        path: Path of the SKILL.md file.
        directory: Path of the skill directory.
        directory_name: Name of the skill directory (the expected skill name).
        raw: Complete file content.
        frontmatter: Parsed frontmatter mapping, or None when missing or unparseable.
        frontmatter_error: Parse error description, or None when the frontmatter parsed.
        body: Markdown body below the frontmatter.
    """

    path: Path
    directory: Path
    directory_name: str
    raw: str
    frontmatter: dict[str, Any] | None = None
    frontmatter_error: str | None = None
    body: str = ""


def parse_skill_md(path: Path) -> Skill:
    """Parse one SKILL.md file into frontmatter and body parts.

    Parsing is lenient: a missing or broken frontmatter is reported through
    ``frontmatter_error`` instead of raising, so validators can produce a
    complete error list.

    Args:
        path: Path of the SKILL.md file to parse.

    Returns:
        The parsed skill; check ``frontmatter_error`` for parse problems.
    """
    raw = path.read_text(encoding="utf-8")
    skill = Skill(path=path, directory=path.parent, directory_name=path.parent.name, raw=raw)

    lines = raw.splitlines()
    if not lines or lines[0].strip() != "---":
        return replace(skill, frontmatter_error="SKILL.md must start with a '---' frontmatter delimiter")

    closing_index = next(
        (index for index in range(1, len(lines)) if lines[index].strip() == "---"),
        None,
    )
    if closing_index is None:
        return replace(skill, frontmatter_error="frontmatter is not terminated by a closing '---' delimiter")

    frontmatter_text = "\n".join(lines[1:closing_index])
    body = "\n".join(lines[closing_index + 1 :])

    try:
        frontmatter = yaml.safe_load(frontmatter_text)
    except yaml.YAMLError as exc:
        return replace(skill, frontmatter_error=f"frontmatter is not valid YAML: {exc}", body=body)

    if not isinstance(frontmatter, dict):
        return replace(
            skill,
            frontmatter_error="frontmatter must be a YAML mapping of field names to values",
            body=body,
        )

    return replace(skill, frontmatter=frontmatter, body=body)


def discover_skills(skills_directory: Path = SKILLS_DIRECTORY) -> list[Skill]:
    """Discover and parse all skills under *skills_directory*.

    Every immediate subdirectory containing a SKILL.md file is a skill. The
    ``.claude/skills`` symlink is not scanned because it points at
    ``.agents/skills`` and would only duplicate the results.

    Args:
        skills_directory: Directory with one subdirectory per skill.

    Returns:
        The parsed skills in sorted directory order.
    """
    return [parse_skill_md(skill_file) for skill_file in sorted(skills_directory.glob(f"*/{SKILL_FILE_NAME}"))]
