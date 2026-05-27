"""Load bundled RBAC JSON data files (no imports from manifest or resolver)."""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from typing import Any


def _data_path(name: str) -> Any:
    return resources.files("insights_mcp.rbac").joinpath("data").joinpath(name)


@lru_cache(maxsize=1)
def load_role_recommendations() -> dict[str, list[str]]:
    """Load role -> permissions mapping from role_recommendations.json."""
    raw = _data_path("role_recommendations.json").read_text(encoding="utf-8")
    return json.loads(raw)


@lru_cache(maxsize=1)
def load_manifest_raw() -> dict[str, Any]:
    """Load tool_rbac_manifest.json as a parsed dict."""
    raw = _data_path("tool_rbac_manifest.json").read_text(encoding="utf-8")
    return json.loads(raw)


@lru_cache(maxsize=1)
def load_upstream_permissions_index() -> dict[str, Any]:
    """Load upstream_permissions.json endpoint index."""
    try:
        raw = _data_path("upstream_permissions.json").read_text(encoding="utf-8")
        return json.loads(raw)
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}
