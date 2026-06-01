"""Tests for scripts/merge_skill_header.py."""

from pathlib import Path

from scripts.merge_skill_header import merge_skill_header, strip_trailing_whitespace


def test_strip_trailing_whitespace_removes_spaces_on_blank_lines():
    """Trailing spaces on empty lines are removed for pre-commit parity."""
    assert strip_trailing_whitespace("line one  \n   \nline two\n") == "line one\n\nline two\n"


def test_merge_skill_header_strips_body_whitespace(tmp_path: Path):
    """Merged SKILL.md has no trailing whitespace on blank docstring lines."""
    header = tmp_path / "header.yaml"
    body = tmp_path / "body.md"
    out = tmp_path / "SKILL.md"
    header.write_text("---\nname: test\n---\n", encoding="utf-8")
    body.write_text("# Tools\n\n        \n\nExample.\n", encoding="utf-8")
    merge_skill_header(header_path=header, body_path=body, out_path=out)
    text = out.read_text(encoding="utf-8")
    assert "        \n" not in text
    assert text.endswith("\n")
