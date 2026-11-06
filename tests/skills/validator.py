"""Format validation for agent skills per the agentskills.io specification.

Checked rules (https://agentskills.io/specification):

* SKILL.md starts with a YAML frontmatter block terminated by ``---``.
* ``name``: required, at most 64 characters, lowercase letters, numbers, and
  hyphens; it must not start or end with a hyphen, must not contain
  consecutive hyphens, and must match the parent directory name.
* ``description``: required, non-empty, at most 1024 characters.
* Optional fields: ``license`` (string), ``compatibility`` (1-500 characters),
  ``metadata`` (string keys to string values), ``allowed-tools`` (string).
* The Markdown body stays below 500 lines.
* Relative file references (Markdown links and backticked paths) resolve
  inside the skill directory.

Each rule has a dedicated ``*_errors`` function so tests can assert one
criterion at a time; ``validate_format`` combines them for the CLI.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any

from tests.skills.discovery import Skill

#: Valid skill names: lowercase letters, numbers, and single hyphens.
NAME_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MAX_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024
MAX_COMPATIBILITY_LENGTH = 500
MAX_BODY_LINES = 500

_MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
_BACKTICK_PATTERN = re.compile(r"`([^`\n]+)`")
_URL_SCHEME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
_PATH_TOKEN_PATTERN = re.compile(r"^[\w./-]+$")
_FILE_EXTENSION_PATTERN = re.compile(r"\.[A-Za-z0-9]+$")


def validate_format(skill: Skill) -> list[str]:
    """Return all format violations for *skill* (empty when valid)."""
    errors = frontmatter_errors(skill)
    if errors:
        return errors
    errors.extend(name_errors(skill))
    errors.extend(description_errors(skill))
    errors.extend(optional_field_errors(skill))
    errors.extend(body_line_errors(skill))
    errors.extend(reference_errors(skill))
    return errors


def frontmatter_errors(skill: Skill) -> list[str]:
    """The frontmatter must parse into a YAML mapping."""
    if skill.frontmatter_error is not None:
        return [skill.frontmatter_error]
    return []


def name_errors(skill: Skill) -> list[str]:
    """The required ``name`` field must follow the spec naming rules."""
    if skill.frontmatter is None:
        return []
    if "name" not in skill.frontmatter or skill.frontmatter["name"] is None:
        return ["frontmatter field 'name' is required"]

    name = skill.frontmatter["name"]
    if not isinstance(name, str):
        return ["frontmatter field 'name' must be a string"]

    errors: list[str] = []
    if len(name) > MAX_NAME_LENGTH:
        errors.append(f"name {name!r} exceeds the maximum length of {MAX_NAME_LENGTH} characters")
    if not NAME_PATTERN.fullmatch(name):
        errors.append(
            f"name {name!r} must only contain lowercase letters, numbers, and single hyphens "
            "(no leading, trailing, or consecutive hyphens)"
        )
    if name != skill.directory_name:
        errors.append(f"name {name!r} does not match the skill directory name {skill.directory_name!r}")
    return errors


def description_errors(skill: Skill) -> list[str]:
    """The required ``description`` field must be a non-empty string of limited length."""
    if skill.frontmatter is None:
        return []
    if "description" not in skill.frontmatter or skill.frontmatter["description"] is None:
        return ["frontmatter field 'description' is required"]

    description = skill.frontmatter["description"]
    if not isinstance(description, str):
        return ["frontmatter field 'description' must be a string"]

    errors: list[str] = []
    if not description.strip():
        errors.append("frontmatter field 'description' must not be empty")
    if len(description) > MAX_DESCRIPTION_LENGTH:
        errors.append(f"description exceeds the maximum length of {MAX_DESCRIPTION_LENGTH} characters")
    return errors


def optional_field_errors(skill: Skill) -> list[str]:
    """Optional frontmatter fields must have the types required by the spec."""
    if skill.frontmatter is None:
        return []
    frontmatter: dict[str, Any] = skill.frontmatter
    errors: list[str] = []

    license_field = frontmatter.get("license")
    if license_field is not None and not isinstance(license_field, str):
        errors.append("frontmatter field 'license' must be a string")

    compatibility = frontmatter.get("compatibility")
    if compatibility is not None:
        if not isinstance(compatibility, str):
            errors.append("frontmatter field 'compatibility' must be a string")
        elif not 1 <= len(compatibility) <= MAX_COMPATIBILITY_LENGTH:
            errors.append(f"compatibility must be 1-{MAX_COMPATIBILITY_LENGTH} characters long")

    metadata = frontmatter.get("metadata")
    if metadata is not None:
        if not isinstance(metadata, dict):
            errors.append("frontmatter field 'metadata' must be a mapping")
        else:
            for key, value in metadata.items():
                if not isinstance(key, str):
                    errors.append("metadata keys must be strings")
                if not isinstance(value, str):
                    errors.append(f'metadata value for {key!r} must be a string (quote numbers, e.g. version: "1.0")')

    allowed_tools = frontmatter.get("allowed-tools")
    if allowed_tools is not None and not isinstance(allowed_tools, str):
        errors.append("frontmatter field 'allowed-tools' must be a space-separated string of tool names")

    return errors


def body_line_errors(skill: Skill) -> list[str]:
    """The Markdown body must stay below 500 lines."""
    line_count = len(skill.body.splitlines())
    if line_count > MAX_BODY_LINES:
        return [
            f"body has {line_count} lines; keep SKILL.md under {MAX_BODY_LINES} lines "
            "and move detailed reference material to separate files"
        ]
    return []


def reference_errors(skill: Skill) -> list[str]:
    """Relative file references must resolve inside the skill directory."""
    errors: list[str] = []
    for target in _iter_relative_link_targets(skill.body):
        if not _reference_exists(skill, target):
            errors.append(f"relative link target {target!r} does not exist in {skill.directory_name}/")
    for token in _iter_backticked_path_tokens(skill.body):
        if not _reference_exists(skill, token):
            errors.append(f"relative path reference {token!r} does not exist in {skill.directory_name}/")
    return errors


def _is_relative_reference(target: str) -> bool:
    """Return True when *target* is a relative path reference (not a URL, anchor, or absolute path)."""
    if _URL_SCHEME_PATTERN.match(target):
        return False
    return not target.startswith(("/", "~"))


def _iter_relative_link_targets(body: str) -> Iterator[str]:
    """Yield relative Markdown link and image targets found in *body*."""
    for match in _MARKDOWN_LINK_PATTERN.finditer(body):
        target = match.group(1).split("#", 1)[0]
        if target and _is_relative_reference(target):
            yield target


def _iter_backticked_path_tokens(body: str) -> Iterator[str]:
    """Yield backticked tokens that look like relative file references.

    Conservative on purpose: only tokens made of path characters that contain
    a slash and a file extension are checked. Prose like ``.cursor/skills/``
    (a directory) or ``mcp.json`` (a bare file name) is not flagged.
    """
    for match in _BACKTICK_PATTERN.finditer(body):
        token = match.group(1).strip()
        if "/" not in token or token.endswith("/"):
            continue
        if not _PATH_TOKEN_PATTERN.fullmatch(token):
            continue
        if not _FILE_EXTENSION_PATTERN.search(token):
            continue
        if _is_relative_reference(token):
            yield token


def _reference_exists(skill: Skill, reference: str) -> bool:
    """Return True when *reference* resolves to an existing path inside the skill directory."""
    return (skill.directory / reference).resolve().exists()
