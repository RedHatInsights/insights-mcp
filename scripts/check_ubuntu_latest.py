#!/usr/bin/env python3
"""Fail when ubuntu-latest is not the pinned GitHub-hosted runner release.

The expected release is ``.github/ubuntu-runner-version``. Jobs receive it
from the ubuntu-runner workflow. A hardcoded ``runs-on: ubuntu-YY.MM`` is
reported. ``runs-on: ubuntu-latest`` is the probe and the label reader.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = REPO_ROOT / ".github" / "ubuntu-runner-version"
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
OS_RELEASE = Path("/etc/os-release")

_VERSION_RE = re.compile(r"\d+\.\d+")
_PINNED_RUNNER_RE = re.compile(r"^\s*runs-on:\s*ubuntu-(?P<version>\d+\.\d+)\s*(?:#.*)?$")


def read_pinned_version(version_file: Path) -> str:
    """Return the runner release stored in ``version_file``.

    Args:
        version_file: File whose contents are a single ``YY.MM`` release.

    Returns:
        The stripped release, for example ``26.04``.

    Raises:
        ValueError: The file is empty or is not a ``YY.MM`` release.
    """
    version = version_file.read_text(encoding="utf-8").strip()
    if _VERSION_RE.fullmatch(version) is None:
        raise ValueError(f"invalid runner version {version!r}: want YY.MM")
    return version


def parse_os_release_version(os_release_text: str) -> str:
    """Return ``VERSION_ID`` from os-release text.

    Args:
        os_release_text: Contents of ``/etc/os-release``.

    Returns:
        The ``VERSION_ID`` value without quotes, for example ``26.04``.

    Raises:
        ValueError: ``VERSION_ID`` is missing or is not a ``YY.MM`` release.
    """
    for line in os_release_text.splitlines():
        if not line.startswith("VERSION_ID="):
            continue
        version_id = line.split("=", 1)[1].strip().strip('"').strip("'")
        if _VERSION_RE.fullmatch(version_id) is None:
            raise ValueError(f"invalid VERSION_ID {version_id!r}: want YY.MM")
        return version_id
    raise ValueError("VERSION_ID missing from os-release")


def pinned_workflow_versions(workflows_dir: Path) -> list[tuple[Path, str]]:
    """Return each numeric ``runs-on: ubuntu-YY.MM`` pin under ``workflows_dir``.

    Args:
        workflows_dir: Directory of GitHub Actions workflow files.

    Returns:
        ``(path, version)`` pairs. ``ubuntu-latest`` lines are omitted.
    """
    pins: list[tuple[Path, str]] = []
    workflow_paths = sorted(workflows_dir.glob("*.yaml")) + sorted(workflows_dir.glob("*.yml"))
    for workflow_path in workflow_paths:
        for line in workflow_path.read_text(encoding="utf-8").splitlines():
            match = _PINNED_RUNNER_RE.match(line)
            if match is None:
                continue
            pins.append((workflow_path, match.group("version")))
    return pins


def hardcoded_pin_message(workflow_path: Path, version: str) -> str:
    """Return the drift message for one hardcoded numeric runner pin.

    Args:
        workflow_path: Workflow file that repeats the release.
        version: Release parsed from that ``runs-on`` line.

    Returns:
        The message telling the author to use the version file instead.
    """
    return (
        f"{workflow_path}: hardcoded runs-on ubuntu-{version}. "
        "Remove it and use needs.ubuntu-runner.outputs.label. "
        "The release belongs in .github/ubuntu-runner-version."
    )


def ubuntu_latest_mismatch(actual: str, expected: str) -> str:
    """Return the message for an ubuntu-latest release that differs from the pin.

    Args:
        actual: ``VERSION_ID`` of the ubuntu-latest runner.
        expected: Release from the version file.

    Returns:
        Versions plus the edit and who should make it.
    """
    return (
        f"ubuntu-latest is {actual}, pinned runner is {expected}.\n"
        f"Set .github/ubuntu-runner-version to {actual}.\n"
        "Please contact a maintainer of this project to bump the GitHub Actions "
        "runner version, or include that change in your PR."
    )


def runner_pin_drift(pins: list[tuple[Path, str]]) -> list[str]:
    """Return messages for hardcoded ``runs-on: ubuntu-YY.MM`` lines.

    Args:
        pins: Numeric runner pins found in workflow files.

    Returns:
        One message per hardcoded pin. An empty list means the version file
        is the only release.
    """
    return [hardcoded_pin_message(workflow_path, version) for workflow_path, version in pins]


def collect_check_errors(expected: str, os_release_text: str, workflows_dir: Path) -> list[str]:
    """Compare a runner's os-release and workflow pins with ``expected``.

    Args:
        expected: Release from the version file.
        os_release_text: os-release contents of the machine running the check.
        workflows_dir: Directory of workflow files to scan for pins.

    Returns:
        Mismatch messages. An empty list means ubuntu-latest matches the
        version file and no workflow hardcodes a release.
    """
    errors = runner_pin_drift(pinned_workflow_versions(workflows_dir))
    actual = parse_os_release_version(os_release_text)
    if actual != expected:
        errors.append(ubuntu_latest_mismatch(actual, expected))
    return errors


def github_warning_commands(message: str) -> list[str]:
    """Return GitHub Actions warning commands for each line of ``message``.

    Args:
        message: Check failure text. Blank lines are skipped.

    Returns:
        ``::warning::`` commands. Annotations are one line each.
    """
    return [f"::warning::{line}" for line in message.splitlines() if line]


def report_errors(errors: list[str], *, warn: bool) -> int:
    """Print check failures and return the process status.

    Args:
        errors: Mismatch messages from :func:`collect_check_errors`.
        warn: When true, print GitHub warning annotations and return success.
            When false, print the messages to stderr and return failure.

    Returns:
        ``0`` for a warning, ``1`` for a failure.
    """
    message = "\n".join(errors)
    if warn:
        for command in github_warning_commands(message):
            print(command)
        return 0
    print(message, file=sys.stderr)
    return 1


def main() -> None:
    """Warn in GitHub Actions, or exit non-zero elsewhere, when the runner check fails."""
    expected = read_pinned_version(VERSION_FILE)
    os_release_text = OS_RELEASE.read_text(encoding="utf-8")
    errors = collect_check_errors(expected, os_release_text, WORKFLOWS_DIR)
    if errors:
        warn = os.environ.get("GITHUB_ACTIONS") == "true"
        raise SystemExit(report_errors(errors, warn=warn))


if __name__ == "__main__":
    main()
