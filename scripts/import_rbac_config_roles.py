#!/usr/bin/env python3
"""Import platform roles from Red Hat rbac-config into role_recommendations.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from insights_mcp.rbac.rbac_config import import_role_recommendations, read_pinned_ref  # noqa: E402

DATA_DIR = REPO_ROOT / "src" / "insights_mcp" / "rbac" / "data"


def main() -> None:
    """Write role_recommendations.json from rbac-config."""
    ref = read_pinned_ref()
    roles = import_role_recommendations(ref=ref)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DATA_DIR / "role_recommendations.json"
    out_path.write_text(json.dumps(roles, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {out_path} ({len(roles)} roles, rbac_config_ref={ref})")


if __name__ == "__main__":
    main()
