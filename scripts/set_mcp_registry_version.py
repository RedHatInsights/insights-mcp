#!/usr/bin/env python3
"""Bump server.json version for MCP Registry publish (registry max + patch/minor + optional SHA)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mcp_registry.version import (
    apply_version_to_server_json,
    compute_next_version,
    fetch_published_versions,
    load_server_json,
    resolve_server_name,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Query the MCP Registry for the latest published version, compute the next "
            "semver (patch by default), optionally append git SHA as build metadata, "
            "and update server.json."
        ),
    )
    parser.add_argument(
        "--server-json",
        type=Path,
        default=REPO_ROOT / "server.json",
        help="Path to server.json (default: repo root server.json)",
    )
    parser.add_argument(
        "--server-name",
        help="MCP Registry server name (default: read from server.json)",
    )
    parser.add_argument(
        "--bump",
        choices=("patch", "minor"),
        default="patch",
        help="Semver component to increment (default: patch)",
    )
    parser.add_argument(
        "--sha",
        help="Git commit SHA to append as semver build metadata (e.g. abc12345)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the computed version without modifying server.json",
    )
    return parser.parse_args()


def main() -> None:
    """Compute next MCP Registry version and update server.json."""
    args = _parse_args()
    server_json_path = args.server_json.resolve()
    if not server_json_path.is_file():
        raise SystemExit(f"server.json not found: {server_json_path}")

    server_data = load_server_json(server_json_path)
    server_name = resolve_server_name(server_data, args.server_name)
    published = fetch_published_versions(server_name)
    next_version = compute_next_version(published, bump=args.bump, sha=args.sha)

    published_text = ", ".join(str(version) for version in sorted(published)) or "(none)"
    print(
        f"Registry {server_name}: published=[{published_text}] -> next={next_version}",
        file=sys.stderr,
    )

    if args.dry_run:
        print(next_version)
        return

    apply_version_to_server_json(server_json_path, next_version)
    print(next_version)


if __name__ == "__main__":
    main()
