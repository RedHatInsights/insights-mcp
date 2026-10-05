#!/usr/bin/env python3
"""Upload ATIF JSON testruns under tests/logs/YYYYMMDDhhmmss/ into Phoenix projects."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
_TESTS_DIR = REPO_ROOT / "tests"
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))

from mcp_llm_eval.atif_export import (  # noqa: E402  pylint: disable=wrong-import-position,import-error
    MISSING_PHOENIX_CLIENT,
    phoenix_collector_endpoint,
    phoenix_project_name,
    require_phoenix_client,
    upload_trajectories,
)

DEFAULT_LOGS_DIR = REPO_ROOT / "tests" / "logs"
RUN_DIR_PATTERN = re.compile(r"^\d{14}$")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest ATIF JSON files from tests/logs/<YYYYMMDDhhmmss>/ as Phoenix projects.",
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=DEFAULT_LOGS_DIR,
        help=f"Testrun parent directory (default: {DEFAULT_LOGS_DIR})",
    )
    parser.add_argument(
        "--run",
        default="",
        help="Ingest only this YYYYMMDDhhmmss testrun folder.",
    )
    parser.add_argument(
        "--endpoint",
        default="",
        help="Phoenix collector endpoint (default: PHOENIX_COLLECTOR_ENDPOINT).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print project <- files mapping without uploading.",
    )
    return parser.parse_args()


def iter_testrun_dirs(logs_dir: Path, run_id: str) -> list[Path]:
    """List testrun directories under ``logs_dir``.

    Args:
        logs_dir: Parent directory that contains YYYYMMDDhhmmss folders.
        run_id: If non-empty, only this folder name is returned.

    Returns:
        Sorted list of testrun directories.

    Raises:
        SystemExit: If ``logs_dir`` is missing or ``run_id`` is invalid / absent.
    """
    if not logs_dir.is_dir():
        raise SystemExit(f"Logs directory not found: {logs_dir}")

    if run_id:
        if not RUN_DIR_PATTERN.match(run_id):
            raise SystemExit(f"Invalid --run value {run_id!r}; expected YYYYMMDDhhmmss")
        run_dir = logs_dir / run_id
        if not run_dir.is_dir():
            raise SystemExit(f"Testrun directory not found: {run_dir}")
        return [run_dir]

    run_dirs = sorted(path for path in logs_dir.iterdir() if path.is_dir() and RUN_DIR_PATTERN.match(path.name))
    if not run_dirs:
        raise SystemExit(f"No YYYYMMDDhhmmss testrun directories under {logs_dir}")
    return run_dirs


def load_atif_json(path: Path) -> dict[str, Any]:
    """Load one ATIF trajectory JSON file.

    Args:
        path: Path to a ``.json`` trajectory.

    Returns:
        Parsed trajectory object.

    Raises:
        SystemExit: If the file is not valid JSON or not an object.
    """
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"ATIF file must be a JSON object: {path}")
    return payload


def collect_run_trajectories(run_dir: Path) -> list[tuple[Path, dict[str, Any]]]:
    """Load all ``*.json`` files in a testrun directory.

    Args:
        run_dir: Testrun folder.

    Returns:
        Pairs of path and parsed trajectory.

    Raises:
        SystemExit: If the folder contains no JSON files.
    """
    json_paths = sorted(run_dir.glob("*.json"))
    if not json_paths:
        raise SystemExit(f"No *.json files in testrun directory: {run_dir}")
    return [(path, load_atif_json(path)) for path in json_paths]


def ingest_run(
    run_dir: Path,
    *,
    dry_run: bool,
    endpoint: str,
) -> None:
    """Print or upload one testrun to Phoenix.

    Args:
        run_dir: Testrun folder named YYYYMMDDhhmmss.
        dry_run: If true, only print the mapping.
        endpoint: Phoenix collector base URL.

    Raises:
        SystemExit: If Phoenix client is missing during a real ingest.
    """
    project_name = phoenix_project_name(run_dir.name)
    files_and_trajectories = collect_run_trajectories(run_dir)
    file_names = ", ".join(path.name for path, _ in files_and_trajectories)
    print(f"{project_name} <- {run_dir} ({file_names})")
    if dry_run:
        return
    if not endpoint:
        raise SystemExit("Set PHOENIX_COLLECTOR_ENDPOINT or pass --endpoint")
    try:
        require_phoenix_client()
    except RuntimeError:
        raise SystemExit(MISSING_PHOENIX_CLIENT) from None
    trajectories = [trajectory for _, trajectory in files_and_trajectories]
    result = upload_trajectories(trajectories, project_name=project_name, endpoint=endpoint)
    print(f"  uploaded: {result}")


def main() -> int:
    """Ingest ATIF testruns into Phoenix.

    Returns:
        Process exit code (0 on success).
    """
    args = _parse_args()
    logs_dir = args.dir if args.dir.is_absolute() else REPO_ROOT / args.dir
    endpoint = args.endpoint.strip() or phoenix_collector_endpoint()
    for run_dir in iter_testrun_dirs(logs_dir, args.run):
        ingest_run(run_dir, dry_run=args.dry_run, endpoint=endpoint)
    return 0


if __name__ == "__main__":
    sys.exit(main())
