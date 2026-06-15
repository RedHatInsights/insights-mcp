#!/usr/bin/env python3
"""Generate catalog-info.yaml by merging static base metadata with live tool primitives."""

from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path
from typing import Any

import yaml

from insights_mcp.catalog_tools import collect_tool_primitives

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_PATH = REPO_ROOT / "catalog-info.base.yaml"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "catalog-info.yaml"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge catalog-info.base.yaml with generated spec.primitives from MCP toolsets.",
    )
    parser.add_argument(
        "--base",
        type=Path,
        default=DEFAULT_BASE_PATH,
        help="Static catalog metadata YAML (default: catalog-info.base.yaml)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Output catalog-info.yaml path (default: catalog-info.yaml)",
    )
    parser.add_argument(
        "--brand-long",
        default="Red Hat Lightspeed",
        help="Value for $container_brand_long in tool descriptions",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if output would differ from the file on disk",
    )
    return parser.parse_args()


def load_base_catalog(base_path: Path) -> str:
    """Load the static catalog-info base YAML text.

    Args:
        base_path: Path to catalog-info.base.yaml.

    Returns:
        Base file contents with trailing whitespace removed.

    Raises:
        SystemExit: If the base file is missing.
    """
    if not base_path.is_file():
        raise SystemExit(f"Base catalog file not found: {base_path}")

    base_text = base_path.read_text(encoding="utf-8").rstrip()
    if not base_text:
        raise SystemExit(f"Base catalog file is empty: {base_path}")

    return base_text


def format_primitives_yaml(primitives: list[dict[str, str]]) -> str:
    """Render spec.primitives as YAML with yamllint-compatible indentation."""
    lines = ["  primitives:"]
    for primitive in primitives:
        lines.append("    - type: tool")
        lines.append(f"      name: {_yaml_scalar(primitive['name'])}")
        lines.append(f"      description: {_yaml_scalar(primitive['description'])}")
    return "\n".join(lines)


def _yaml_scalar(value: str) -> str:
    """Return a YAML scalar, quoting when required."""
    if not value:
        return '""'
    if _needs_yaml_quotes(value):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return value


def _needs_yaml_quotes(value: str) -> bool:
    """Return True when a plain scalar would be ambiguous in YAML."""
    if value[0] in "'\"@`:{}[],&*#?|-<>=!%":
        return True
    if ":" in value or "#" in value:
        return True
    if value.lower() in {"true", "false", "null", "yes", "no", "on", "off"}:
        return True
    return any(character.isspace() for character in value)


def build_catalog_yaml(base_text: str, *, brand_long: str) -> str:
    """Merge base catalog text with generated tool primitives.

    Args:
        base_text: Static catalog YAML without a primitives section.
        brand_long: Brand name for description template substitution.

    Returns:
        Complete catalog-info.yaml contents.
    """
    primitives = collect_tool_primitives(brand_long=brand_long)
    return f"{base_text}\n{format_primitives_yaml(primitives)}\n"


def validate_catalog_yaml(catalog_yaml: str) -> dict[str, Any]:
    """Parse generated catalog YAML to catch syntax errors early."""
    document = yaml.safe_load(catalog_yaml)
    if not isinstance(document, dict):
        raise ValueError("Generated catalog-info.yaml must contain a mapping")
    return document


def main() -> None:
    """Generate or verify catalog-info.yaml."""
    args = _parse_args()
    base_path = args.base.resolve()
    output_path = args.output.resolve()

    base_text = load_base_catalog(base_path)
    rendered = build_catalog_yaml(base_text, brand_long=args.brand_long)
    validate_catalog_yaml(rendered)

    if args.check:
        if not output_path.is_file():
            print(f"catalog-info.yaml not found: {output_path}", file=sys.stderr)
            raise SystemExit(1)
        existing = output_path.read_text(encoding="utf-8")
        if existing != rendered:
            diff = difflib.unified_diff(
                existing.splitlines(keepends=True),
                rendered.splitlines(keepends=True),
                fromfile=str(output_path),
                tofile=f"{output_path} (generated)",
            )
            sys.stdout.writelines(diff)
            print(
                "catalog-info.yaml is out of date; run: make catalog-info.yaml",
                file=sys.stderr,
            )
            raise SystemExit(1)
        return

    output_path.write_text(rendered, encoding="utf-8")
    print(f"Wrote {output_path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
