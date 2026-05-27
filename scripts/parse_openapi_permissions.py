#!/usr/bin/env python3
"""Index RBAC permission hints from vendored OpenAPI specs."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
APIS_DIR = REPO_ROOT / "apis"

# app:resource:verb or app:*:*
PERMISSION_RE = re.compile(
    r"\b([a-z][a-z0-9_-]*:[a-z0-9_.*-]+:[a-z*]+|[a-z][a-z0-9_-]*:\*:\*)\b",
    re.IGNORECASE,
)


def _normalize_path(path: str) -> str:
    if not path.startswith("/"):
        return "/" + path
    return path


def _extract_permissions(text: str) -> list[str]:
    found = PERMISSION_RE.findall(text or "")
    return sorted(set(p.lower() if ":" in p else p for p in found))


def index_openapi_file(spec_path: Path) -> dict[str, dict[str, Any]]:
    """Return map of METHOD path -> permission metadata."""
    data = json.loads(spec_path.read_text(encoding="utf-8"))
    index: dict[str, dict[str, Any]] = {}
    for path, methods in data.get("paths", {}).items():
        path_norm = _normalize_path(path)
        for method, operation in methods.items():
            if method.lower() in ("parameters", "servers", "summary", "description"):
                continue
            if not isinstance(operation, dict):
                continue
            method_upper = method.upper()
            if method_upper not in ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"):
                continue
            desc = " ".join(
                filter(
                    None,
                    [
                        operation.get("summary", ""),
                        operation.get("description", ""),
                    ],
                )
            )
            perms = _extract_permissions(desc)
            if not perms:
                continue
            key = f"{method_upper} {path_norm}"
            index[key] = {
                "method": method_upper,
                "path": path_norm,
                "required_v1_permissions": [perms],
                "openapi_source": str(spec_path.relative_to(REPO_ROOT)),
                "verified": False,
            }
    return index


def build_openapi_permission_index(api_dir: Path | None = None) -> dict[str, dict[str, Any]]:
    """Index all apis/*.json files."""
    directory = api_dir or APIS_DIR
    combined: dict[str, dict[str, Any]] = {}
    for spec_path in sorted(directory.glob("*-openapi.json")):
        combined.update(index_openapi_file(spec_path))
    return combined


def lookup_endpoint(
    index: dict[str, dict[str, Any]],
    method: str,
    path_template: str,
) -> dict[str, Any] | None:
    """Find index entry for method + path template."""
    method_upper = method.upper()
    path_norm = _normalize_path(path_template)
    direct = f"{method_upper} {path_norm}"
    if direct in index:
        return index[direct]
    for key, entry in index.items():
        if not key.startswith(method_upper + " "):
            continue
        indexed_path = entry["path"]
        if indexed_path == path_norm:
            return entry
    return None


def main() -> None:
    """Print index size for debugging."""
    index = build_openapi_permission_index()
    print(f"Indexed {len(index)} operations with permission hints")


if __name__ == "__main__":
    main()
