#!/usr/bin/env python3
"""Generate test_prompts.md from a toolset test_prompts.py module."""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path
from typing import Any


def _load_prompt_module(module_name: str) -> Any:
    from insights_mcp.test_prompts_data import PromptRegistry

    module = importlib.import_module(module_name)
    if not hasattr(module, "TOOLSET_TITLE"):
        raise ValueError(f"{module_name} must define TOOLSET_TITLE")
    if not hasattr(module, "PROMPTS"):
        raise ValueError(f"{module_name} must define PROMPTS")
    if not isinstance(module.PROMPTS, PromptRegistry):
        raise ValueError(f"{module_name}.PROMPTS must be a PromptRegistry instance")
    return module


def main() -> int:
    """Build test_prompts.md from the given toolset prompts module."""
    parser = argparse.ArgumentParser(description="Generate test_prompts.md from a toolset module.")
    parser.add_argument(
        "--module",
        required=True,
        help="Python module path (e.g. image_builder_mcp.test_prompts)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        required=True,
        help="Output markdown file path (e.g. src/image_builder_mcp/test_prompts.md)",
    )
    args = parser.parse_args()

    from insights_mcp.test_prompts_data import collect_markdown_prompts
    from insights_mcp.test_prompts_markdown import format_bullet_prompts

    module = _load_prompt_module(args.module)
    prompt_texts = collect_markdown_prompts(module.PROMPTS)
    markdown = format_bullet_prompts(module.TOOLSET_TITLE, prompt_texts)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown, encoding="utf-8")
    print(f"Wrote {args.output} ({len(prompt_texts)} prompts)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
