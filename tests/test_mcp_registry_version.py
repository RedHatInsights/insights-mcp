"""Tests for MCP Registry publish version bump scripts."""

from __future__ import annotations

import io
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from mcp_registry.version import (
    apply_version_to_server_json,
    bump_version,
    compute_next_version,
    fetch_published_versions,
    normalize_sha,
    resolve_server_name,
)
from packaging.version import Version


def test_normalize_sha_short_and_long():
    """Short SHAs are lowercased; longer SHAs are truncated to eight characters."""
    assert normalize_sha("AbCdEf01") == "abcdef01"
    assert normalize_sha("abcdef0123456789") == "abcdef01"


def test_normalize_sha_invalid():
    """Non-hex SHAs raise ValueError."""
    with pytest.raises(ValueError, match="invalid sha"):
        normalize_sha("not-hex")


def test_bump_patch_and_minor():
    """Patch and minor bumps advance semver as expected."""
    assert str(bump_version(Version("1.0.0"), "patch")) == "1.0.1"
    assert str(bump_version(Version("1.2.9"), "minor")) == "1.3.0"


def test_compute_next_version_with_sha():
    """Next version increments past published and appends SHA build metadata."""
    published = [Version("1.0.0"), Version("1.0.1+abc12345")]
    assert compute_next_version(published, sha="deadbeef") == "1.0.2+deadbeef"


def test_compute_next_version_empty_published():
    """First publish starts at 1.0.0 with optional SHA metadata."""
    assert compute_next_version([], sha="abc12345") == "1.0.0+abc12345"


def test_resolve_server_name_from_json():
    """Server name comes from server.json unless overridden."""
    assert resolve_server_name({"name": "io.github.example/demo"}, None) == "io.github.example/demo"
    assert resolve_server_name({"name": "io.github.example/demo"}, "override") == "override"


def test_fetch_published_versions_parses_payload():
    """Registry API JSON is parsed into a list of Version objects."""
    payload = {
        "servers": [
            {"server": {"version": "1.0.0"}},
            {"server": {"version": "1.0.1+abc12345"}},
        ],
    }
    body = io.BytesIO(json.dumps(payload).encode("utf-8"))
    response = MagicMock()
    response.__enter__.return_value = body
    response.__exit__.return_value = None

    opener = MagicMock()
    opener.open.return_value = response

    versions = fetch_published_versions("io.github.example/demo", opener=opener)
    assert versions == [Version("1.0.0"), Version("1.0.1+abc12345")]


def test_apply_version_to_server_json(tmp_path: Path):
    """apply_version_to_server_json updates the version field on disk."""
    server_json = tmp_path / "server.json"
    server_json.write_text(
        json.dumps({"name": "io.github.example/demo", "version": "1.0.0"}, indent=2) + "\n",
        encoding="utf-8",
    )
    apply_version_to_server_json(server_json, "1.0.1+abc12345")
    updated = json.loads(server_json.read_text(encoding="utf-8"))
    assert updated["version"] == "1.0.1+abc12345"
