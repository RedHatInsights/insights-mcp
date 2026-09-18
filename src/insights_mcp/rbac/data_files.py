"""Load curated tool REST mappings (no generated JSON)."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from insights_mcp.rbac.rbac_config import REPO_ROOT

_DEFAULT_REST_MAP = REPO_ROOT / "configs" / "tool_rest_map.json"


def tool_rest_map_path() -> Path:
    """Resolve tool_rest_map.json from env or the repository configs directory."""
    env_path = os.environ.get("INSIGHTS_MCP_TOOL_REST_MAP", "").strip()
    if env_path:
        return Path(env_path)
    return _DEFAULT_REST_MAP


@lru_cache(maxsize=1)
def load_tool_rest_map() -> dict[str, Any]:
    """Load configs/tool_rest_map.json as a parsed dict."""
    path = tool_rest_map_path()
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError(f"tool rest map must be an object, got {type(data).__name__} from {path}")
    return data
