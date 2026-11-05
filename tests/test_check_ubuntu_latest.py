"""Tests for the ubuntu-latest runner pin check."""

from __future__ import annotations

from pathlib import Path

import pytest
from check_ubuntu_latest import (
    VERSION_FILE,
    WORKFLOWS_DIR,
    collect_check_errors,
    github_warning_commands,
    hardcoded_pin_message,
    parse_os_release_version,
    pinned_workflow_versions,
    read_pinned_version,
    report_errors,
    runner_pin_drift,
    ubuntu_latest_mismatch,
)

UBUNTU_2604_OS_RELEASE = """\
PRETTY_NAME="Ubuntu 26.04.1 LTS"
NAME="Ubuntu"
VERSION_ID="26.04"
VERSION="26.04.1 LTS (Resolute Raccoon)"
VERSION_CODENAME=resolute
ID=ubuntu
"""


def test_parse_os_release_version_quoted_and_unquoted():
    """Quoted and bare VERSION_ID values are the same release."""
    assert parse_os_release_version('VERSION_ID="26.04"\n') == "26.04"
    assert parse_os_release_version("VERSION_ID=26.04\n") == "26.04"


def test_parse_os_release_version_from_ubuntu_image():
    """A realistic os-release block yields the VERSION_ID release."""
    assert parse_os_release_version(UBUNTU_2604_OS_RELEASE) == "26.04"


def test_parse_os_release_version_missing():
    """os-release without VERSION_ID is rejected."""
    with pytest.raises(ValueError, match="VERSION_ID missing from os-release"):
        parse_os_release_version("NAME=Ubuntu\n")


def test_parse_os_release_version_invalid():
    """A non YY.MM VERSION_ID is rejected with the actual value."""
    with pytest.raises(ValueError, match="invalid VERSION_ID 'rolling': want YY.MM"):
        parse_os_release_version("VERSION_ID=rolling\n")


def test_read_pinned_version_invalid(tmp_path: Path):
    """A version file that is not YY.MM is rejected with the actual value."""
    version_file = tmp_path / "ubuntu-runner-version"
    version_file.write_text("latest\n", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid runner version 'latest': want YY.MM"):
        read_pinned_version(version_file)


def test_runner_pin_drift_reports_hardcoded_release(tmp_path: Path):
    """ubuntu-latest is allowed. A numeric runs-on is not, even when it matches."""
    build_workflow = tmp_path / "build.yaml"
    build_workflow.write_text("    runs-on: ubuntu-26.04\n", encoding="utf-8")
    (tmp_path / "probe.yaml").write_text("    runs-on: ubuntu-latest\n", encoding="utf-8")
    pins = pinned_workflow_versions(tmp_path)
    assert pins == [(build_workflow, "26.04")]
    assert runner_pin_drift(pins) == [hardcoded_pin_message(build_workflow, "26.04")]


def test_runner_pin_drift_allows_dynamic_label(tmp_path: Path):
    """A job that takes the label from ubuntu-runner is not a hardcoded pin."""
    (tmp_path / "lint.yaml").write_text(
        "    runs-on: ${{ needs.ubuntu-runner.outputs.label }}\n",
        encoding="utf-8",
    )
    assert runner_pin_drift(pinned_workflow_versions(tmp_path)) == []


def test_runner_pin_drift_missing_pins(tmp_path: Path):
    """A tree with only ubuntu-latest has nothing to hardcode."""
    (tmp_path / "probe.yaml").write_text("    runs-on: ubuntu-latest\n", encoding="utf-8")
    pins = pinned_workflow_versions(tmp_path)
    assert not pins
    assert runner_pin_drift(pins) == []


def test_collect_check_errors_reports_runner_and_pin(tmp_path: Path):
    """A moved ubuntu-latest and a hardcoded pin are both reported."""
    build_workflow = tmp_path / "build.yaml"
    build_workflow.write_text("    runs-on: ubuntu-26.04\n", encoding="utf-8")
    errors = collect_check_errors("26.04", 'VERSION_ID="28.04"\n', tmp_path)
    assert errors == [
        hardcoded_pin_message(build_workflow, "26.04"),
        ubuntu_latest_mismatch("28.04", "26.04"),
    ]


def test_ubuntu_latest_mismatch_tells_what_to_edit():
    """The mismatch names the file to set and who should change it."""
    message = ubuntu_latest_mismatch("28.04", "26.04")
    assert "ubuntu-latest is 28.04, pinned runner is 26.04." in message
    assert "Set .github/ubuntu-runner-version to 28.04." in message
    assert "contact a maintainer of this project" in message
    assert "include that change in your PR" in message


def test_github_warning_commands_keep_each_line():
    """Each line of a mismatch becomes its own warning annotation."""
    message = ubuntu_latest_mismatch("28.04", "26.04")
    commands = github_warning_commands(message)
    assert commands[0] == "::warning::ubuntu-latest is 28.04, pinned runner is 26.04."
    assert commands[1] == "::warning::Set .github/ubuntu-runner-version to 28.04."
    assert any("include that change in your PR." in command for command in commands)
    assert all("\n" not in command for command in commands)


def test_report_errors_warn_exits_successfully(capsys: pytest.CaptureFixture[str]):
    """A warning prints annotations and does not fail the process."""
    message = ubuntu_latest_mismatch("28.04", "26.04")
    status = report_errors([message], warn=True)
    captured = capsys.readouterr()
    assert status == 0
    assert captured.err == ""
    assert captured.out == "\n".join(github_warning_commands(message)) + "\n"


def test_report_errors_without_warn_fails(capsys: pytest.CaptureFixture[str]):
    """Outside GitHub Actions the same text is a failed check."""
    status = report_errors(["ubuntu-latest is 28.04, pinned runner is 26.04."], warn=False)
    captured = capsys.readouterr()
    assert status == 1
    assert captured.out == ""
    assert captured.err == "ubuntu-latest is 28.04, pinned runner is 26.04.\n"


def test_repository_workflows_do_not_hardcode_runner_release():
    """The version file is a YY.MM release and workflows do not repeat it."""
    read_pinned_version(VERSION_FILE)
    assert runner_pin_drift(pinned_workflow_versions(WORKFLOWS_DIR)) == []
