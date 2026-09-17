#!/usr/bin/env python3
"""Prepare MkDocs staging files under docs/mkdocs/ from root documentation sources."""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MKDOCS_DIR = PROJECT_ROOT / "docs" / "mkdocs"
GITHUB_BLOB_BASE = "https://github.com/RedHatInsights/insights-mcp/blob/main"

# Root-authored sources copied and patched for MkDocs link resolution.
PATCHED_SOURCES: dict[Path, Path] = {
    PROJECT_ROOT / "README.md": MKDOCS_DIR / "index.md",
    PROJECT_ROOT / "HACKING.md": MKDOCS_DIR / "HACKING.md",
}

# Generated root files exposed via symlinks (relative to docs/mkdocs/).
SYMLINK_SOURCES: dict[str, Path] = {
    "usage.md": PROJECT_ROOT / "usage.md",
    "toolsets.md": PROJECT_ROOT / "toolsets.md",
}

# Static assets copied into docs/mkdocs/ (MkDocs cannot reliably copy symlinked files).
COPIED_ASSETS: dict[str, Path] = {
    "architecture-structure.svg": PROJECT_ROOT / "docs" / "architecture-structure.svg",
    "architecture-deployment.svg": PROJECT_ROOT / "docs" / "architecture-deployment.svg",
}


# GitHub and MkDocs slugify headings differently (e.g. "&" becomes "--" on GitHub, "-" in MkDocs).
GITHUB_TO_MKDOCS_ANCHORS: dict[str, str] = {
    "security--incident-response-emergency-revocation": "security-incident-response-emergency-revocation",
}


def patch_for_mkdocs(content: str) -> str:
    """Rewrite root-relative markdown links for rendering from docs/mkdocs/."""
    content = content.replace("](docs/architecture-", "](architecture-")
    content = content.replace("](docs/", "](../")
    content = content.replace("](README.md", "](index.md")
    content = content.replace("](src/", f"]({GITHUB_BLOB_BASE}/src/")
    for github_anchor, mkdocs_anchor in GITHUB_TO_MKDOCS_ANCHORS.items():
        content = content.replace(f"#{github_anchor}", f"#{mkdocs_anchor}")
    return content


def write_patched_file(source: Path, destination: Path) -> None:
    """Copy a root markdown file into docs/mkdocs/ with link patches applied."""
    patched_content = patch_for_mkdocs(source.read_text(encoding="utf-8"))
    destination.write_text(patched_content, encoding="utf-8")


def ensure_symlink(name: str, target: Path) -> None:
    """Create or refresh a symlink under docs/mkdocs/ pointing at target."""
    link_path = MKDOCS_DIR / name
    relative_target = os.path.relpath(target, MKDOCS_DIR)

    if link_path.is_symlink():
        if link_path.resolve() == target.resolve():
            return
        link_path.unlink()
    elif link_path.exists():
        link_path.unlink()

    link_path.symlink_to(relative_target)


def copy_asset(name: str, source: Path) -> None:
    """Copy a static asset into docs/mkdocs/."""
    destination = MKDOCS_DIR / name
    if destination.is_symlink() or destination.exists():
        destination.unlink()
    destination.write_bytes(source.read_bytes())


def main() -> int:
    """Generate patched copies and symlinks for the MkDocs docs_dir."""
    MKDOCS_DIR.mkdir(parents=True, exist_ok=True)

    for source, destination in PATCHED_SOURCES.items():
        if not source.is_file():
            print(f"error: missing source file: {source}", file=sys.stderr)
            return 1
        write_patched_file(source, destination)

    for name, target in SYMLINK_SOURCES.items():
        if not target.is_file():
            print(f"error: missing symlink target: {target}", file=sys.stderr)
            return 1
        ensure_symlink(name, target)

    for name, source in COPIED_ASSETS.items():
        if not source.is_file():
            print(f"error: missing asset file: {source}", file=sys.stderr)
            return 1
        copy_asset(name, source)

    return 0


if __name__ == "__main__":
    sys.exit(main())
