#!/usr/bin/env python3
"""Merge OpenClaw SKILL.md header template with fastmcp-generated skill body."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def strip_trailing_whitespace(text: str) -> str:
    """Remove trailing whitespace from each line (matches pre-commit trailing-whitespace)."""
    lines = [line.rstrip() for line in text.splitlines()]
    if not lines:
        return ""
    return "\n".join(lines) + "\n"


def merge_skill_header(*, header_path: Path, body_path: Path, out_path: Path) -> None:
    header = strip_trailing_whitespace(header_path.read_text(encoding="utf-8")).strip()
    body = strip_trailing_whitespace(body_path.read_text(encoding="utf-8")).strip()
    if body.startswith("---"):
        body_lines = body.splitlines()
        end = 0
        for index, line in enumerate(body_lines[1:], start=1):
            if line.strip() == "---":
                end = index + 1
                break
        if end:
            body = "\n".join(body_lines[end:]).strip()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        strip_trailing_whitespace(f"{header}\n\n{body}\n"),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge SKILL.md header and body.")
    parser.add_argument("--header", type=Path, required=True)
    parser.add_argument("--body", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    for path in (args.header, args.body):
        if not path.is_file():
            print(f"file not found: {path}", file=sys.stderr)
            sys.exit(1)
    merge_skill_header(header_path=args.header, body_path=args.body, out_path=args.out)


if __name__ == "__main__":
    main()
