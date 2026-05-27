"""Version bump logic for MCP Registry server.json publish."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Literal

from packaging.version import Version

REGISTRY_API_BASE = "https://registry.modelcontextprotocol.io/v0.1"
SHA_PATTERN = re.compile(r"^[0-9a-fA-F]{7,40}$")
BumpKind = Literal["patch", "minor"]


def normalize_sha(sha: str) -> str:
    """Return a lowercase git SHA (8 chars when longer is provided)."""
    trimmed = sha.strip().lower()
    if not SHA_PATTERN.match(trimmed):
        raise ValueError(f"invalid sha: got {sha!r}, want 7-40 hexadecimal characters")
    return trimmed[:8] if len(trimmed) > 8 else trimmed


def fetch_published_versions(
    server_name: str,
    *,
    opener: urllib.request.OpenerDirector | None = None,
    timeout_seconds: float = 30.0,
) -> list[Version]:
    """Return all published semver versions for an MCP Registry server name."""
    encoded_name = urllib.parse.quote(server_name, safe="")
    url = f"{REGISTRY_API_BASE}/servers/{encoded_name}/versions"
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    open_url = opener.open if opener is not None else urllib.request.urlopen
    try:
        with open_url(request, timeout=timeout_seconds) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return []
        raise

    versions: list[Version] = []
    for entry in payload.get("servers", []):
        version_text = entry.get("server", {}).get("version")
        if version_text:
            versions.append(Version(version_text))
    return versions


def bump_version(max_published: Version, bump: BumpKind) -> Version:
    """Return the next semver after max_published for patch or minor bump."""
    if bump == "patch":
        return Version(f"{max_published.major}.{max_published.minor}.{max_published.micro + 1}")
    if bump == "minor":
        return Version(f"{max_published.major}.{max_published.minor + 1}.0")
    raise ValueError(f"invalid bump: got {bump!r}, want 'patch' or 'minor'")


def compute_next_version(
    published: list[Version],
    *,
    bump: BumpKind = "patch",
    sha: str | None = None,
) -> str:
    """
    Compute the next registry version strictly greater than all published versions.

    When sha is set, append it as semver build metadata (e.g. 1.0.1+abc12345).
    """
    if published:
        next_version = bump_version(max(published), bump)
    else:
        # First publication for a new server name: start at 1.0.0 (not 0.0.1).
        next_version = Version("1.0.0")
    version_text = str(next_version)
    if sha is not None:
        version_text = f"{version_text}+{normalize_sha(sha)}"
    return version_text


def load_server_json(path: Path) -> dict:
    """Load server.json as a dict."""
    return json.loads(path.read_text(encoding="utf-8"))


def write_server_json(path: Path, data: dict) -> None:
    """Write server.json with stable formatting."""
    path.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def apply_version_to_server_json(path: Path, version: str) -> dict:
    """Set the top-level version field in server.json and return the updated dict."""
    data = load_server_json(path)
    data["version"] = version
    write_server_json(path, data)
    return data


def resolve_server_name(server_json: dict, override: str | None) -> str:
    """Return the MCP Registry server name from server.json or an override."""
    if override is not None:
        return override
    name = server_json.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("server.json is missing a non-empty 'name' field")
    return name
