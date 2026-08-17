#!/usr/bin/env python3
"""Generate test_prompts.md from a toolset test_prompts.py module."""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path
from typing import Any

# The prompt registries use the test-only mcp_llm_eval package. Keep this script
# runnable directly without requiring callers to configure PYTHONPATH.
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "tests"))

# Doc-only examples for generated test_prompts.md (never used at test runtime).
MARKDOWN_PLACEHOLDER_EXAMPLES: dict[str, str] = {
    "cve_id": "CVE-2024-1234",
    "system_id": "12345678-1234-1234-1234-123456789abc",
    "host_id": "12345678-1234-1234-1234-123456789abc",
    "hostname": "web-server-prod-01",
    "host_ids": "12345678-1234-1234-1234-123456789abc, 87654321-4321-4321-4321-ba9876543210",
    "rule_id": "network_firewall_zone_drift_enabled|ENABLE_FIREWALL_ZONE_DRIFTING_WARN",
    "workspace": "your_workspace",
    "satellite_tag": "lifecycle_environment=Prod",
    "rbac_username": "john.doe",
}


def _load_prompt_module(module_name: str) -> Any:
    from mcp_llm_eval.data import PromptRegistry

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

    from mcp_llm_eval.data import collect_markdown_prompts

    from insights_mcp.test_prompts_markdown import format_bullet_prompts

    module = _load_prompt_module(args.module)
    prompt_texts = collect_markdown_prompts(module.PROMPTS, MARKDOWN_PLACEHOLDER_EXAMPLES)
    markdown = format_bullet_prompts(module.TOOLSET_TITLE, prompt_texts)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown, encoding="utf-8")
    print(f"Wrote {args.output} ({len(prompt_texts)} prompts)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
