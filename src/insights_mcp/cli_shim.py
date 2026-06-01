"""Console entry points for brand-aware generated tool CLIs."""

from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path

_BRAND_FILES = {
    "insights": "insights-mcp-cli.py",
    "red-hat-lightspeed": "red-hat-lightspeed-mcp-cli.py",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _generated_cli_path(brand: str) -> Path:
    filename = _BRAND_FILES[brand]
    path = _repo_root() / "generated" / filename
    if path.is_file():
        return path
    raise FileNotFoundError(f"Missing generated CLI at {path}. Run: make generate-cli-all")


def _run_brand(brand: str) -> None:
    os.environ.setdefault("CONTAINER_BRAND", brand)
    cli_path = _generated_cli_path(brand)
    sys.argv[0] = str(cli_path)
    runpy.run_path(str(cli_path), run_name="__main__")


def main_insights() -> None:
    """Entry point for insights-mcp-cli console script."""
    _run_brand("insights")


def main_lightspeed() -> None:
    """Entry point for red-hat-lightspeed-mcp-cli console script."""
    _run_brand("red-hat-lightspeed")
