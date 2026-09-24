"""Format test prompt collections as markdown bullet lists."""

from __future__ import annotations

from typing import Sequence


def format_bullet_prompts(title: str, prompts: Sequence[str]) -> str:
    """Return a markdown heading and bullet list of prompts."""
    lines = [f"# {title}", ""]
    lines.extend(f"- {prompt}" for prompt in prompts)
    lines.append("")
    return "\n".join(lines)
