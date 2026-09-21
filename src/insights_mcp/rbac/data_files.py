"""Load curated tool REST mappings shipped with the package."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any


def tool_rest_map_path() -> Path | None:
    """Return an explicit rest-map path from the environment, if set."""
    env_path = os.environ.get("INSIGHTS_MCP_TOOL_REST_MAP", "").strip()
    if env_path:
        return Path(env_path)
    return None


def _read_packaged_rest_map() -> str:
    """Read tool_rest_map.json from package data (works in wheels and containers)."""
    rest_map = resources.files("insights_mcp.rbac").joinpath("data").joinpath("tool_rest_map.json")
    return rest_map.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def load_tool_rest_map() -> dict[str, Any]:
    """Load the tool REST map from env override or packaged JSON."""
    explicit = tool_rest_map_path()
    if explicit is not None:
        raw = explicit.read_text(encoding="utf-8")
        source = str(explicit)
    else:
        raw = _read_packaged_rest_map()
        source = "package:insights_mcp.rbac/data/tool_rest_map.json"
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError(f"tool rest map must be an object, got {type(data).__name__} from {source}")
    return data
