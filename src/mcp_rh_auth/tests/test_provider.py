"""Tests for mcp_rh_auth.provider — build_auth_provider and helpers."""

from unittest.mock import MagicMock, patch

import pytest

from mcp_rh_auth.provider import (
    _DEFAULT_SCOPES,
    _resolve_mcp_base_url,
    _resolve_scopes,
    build_auth_provider,
)

# ---------------------------------------------------------------------------
# _resolve_scopes
# ---------------------------------------------------------------------------


def test_resolve_scopes_explicit_takes_precedence(monkeypatch):
    monkeypatch.setenv("AUTH_SCOPES", "env.scope1,env.scope2")
    result = _resolve_scopes("AUTH_SCOPES", ["explicit.scope"])
    assert result == ["explicit.scope"]


def test_resolve_scopes_from_env(monkeypatch):
    monkeypatch.setenv("AUTH_SCOPES", "openid, api.console, api.ocm")
    result = _resolve_scopes("AUTH_SCOPES", None)
    assert result == ["openid", "api.console", "api.ocm"]


def test_resolve_scopes_default_when_neither(monkeypatch):
    monkeypatch.delenv("AUTH_SCOPES", raising=False)
    result = _resolve_scopes("AUTH_SCOPES", None)
    assert result == _DEFAULT_SCOPES


# ---------------------------------------------------------------------------
# _resolve_mcp_base_url
# ---------------------------------------------------------------------------


def test_resolve_mcp_base_url_from_mcp_base_url(monkeypatch):
    monkeypatch.setenv("MCP_BASE_URL", "https://my-mcp.example.com")
    monkeypatch.delenv("AUTH_RESOURCE", raising=False)
    assert _resolve_mcp_base_url() == "https://my-mcp.example.com"


def test_resolve_mcp_base_url_strips_trailing_slash(monkeypatch):
    monkeypatch.setenv("MCP_BASE_URL", "https://my-mcp.example.com/")
    monkeypatch.delenv("AUTH_RESOURCE", raising=False)
    assert _resolve_mcp_base_url() == "https://my-mcp.example.com"


def test_resolve_mcp_base_url_mcp_base_url_takes_priority(monkeypatch):
    monkeypatch.setenv("MCP_BASE_URL", "https://my-mcp.example.com")
    monkeypatch.setenv("AUTH_RESOURCE", "https://other.example.com/mcp")
    assert _resolve_mcp_base_url() == "https://my-mcp.example.com"


def test_resolve_mcp_base_url_falls_back_to_auth_resource(monkeypatch):
    monkeypatch.delenv("MCP_BASE_URL", raising=False)
    monkeypatch.setenv("AUTH_RESOURCE", "https://custom.example.com/mcp")
    assert _resolve_mcp_base_url() == "https://custom.example.com"


def test_resolve_mcp_base_url_empty_when_neither_set(monkeypatch):
    monkeypatch.delenv("MCP_BASE_URL", raising=False)
    monkeypatch.delenv("AUTH_RESOURCE", raising=False)
    assert _resolve_mcp_base_url() == ""


# ---------------------------------------------------------------------------
# build_auth_provider
# ---------------------------------------------------------------------------


def test_build_auth_provider_no_auth_server(monkeypatch):
    """Returns None when AUTH_SERVER is unset — no-op / stdio mode."""
    monkeypatch.delenv("AUTH_SERVER", raising=False)
    assert build_auth_provider() is None


def test_build_auth_provider_missing_issuer(monkeypatch):
    """Raises ValueError when AUTH_SERVER is set but AUTH_ISSUER is missing."""
    monkeypatch.setenv("AUTH_SERVER", "https://sso.example.com")
    monkeypatch.delenv("AUTH_ISSUER", raising=False)
    monkeypatch.delenv("AUTH_JWKS_URI", raising=False)
    monkeypatch.setenv("MCP_BASE_URL", "https://mcp.example.com")

    with pytest.raises(ValueError, match="AUTH_ISSUER is required"):
        build_auth_provider()


def test_build_auth_provider_with_jwks_uri_override(monkeypatch):
    """When AUTH_JWKS_URI is set, no metadata discovery HTTP call is made."""
    monkeypatch.setenv("AUTH_SERVER", "https://sso.example.com")
    monkeypatch.setenv("AUTH_ISSUER", "https://sso.example.com/realms/redhat-external")
    monkeypatch.setenv("AUTH_JWKS_URI", "https://sso.example.com/realms/redhat-external/protocol/openid-connect/certs")
    monkeypatch.setenv("MCP_BASE_URL", "https://mcp.example.com")

    with patch("mcp_rh_auth.provider._fetch_authorization_server_metadata") as mock_fetch:
        result = build_auth_provider(
            required_scopes=["openid"],
            audience=["mcp"],
        )

    mock_fetch.assert_not_called()
    assert result is not None


def test_build_auth_provider_fetches_metadata(monkeypatch):
    """When AUTH_JWKS_URI is unset, metadata discovery is attempted."""
    monkeypatch.setenv("AUTH_SERVER", "https://sso.example.com")
    monkeypatch.setenv("AUTH_ISSUER", "https://sso.example.com/realms/redhat-external")
    monkeypatch.delenv("AUTH_JWKS_URI", raising=False)
    monkeypatch.setenv("MCP_BASE_URL", "https://mcp.example.com")

    fake_metadata = {"jwks_uri": "https://sso.example.com/realms/redhat-external/protocol/openid-connect/certs"}

    with patch("mcp_rh_auth.provider._fetch_authorization_server_metadata", return_value=fake_metadata):
        result = build_auth_provider(required_scopes=["openid"], audience=["mcp"])

    assert result is not None


def test_build_auth_provider_metadata_fallback(monkeypatch):
    """First metadata endpoint missing jwks_uri → falls back to second endpoint."""
    monkeypatch.setenv("AUTH_SERVER", "https://sso.example.com")
    monkeypatch.setenv("AUTH_ISSUER", "https://sso.example.com/realms/redhat-external")
    monkeypatch.delenv("AUTH_JWKS_URI", raising=False)
    monkeypatch.setenv("MCP_BASE_URL", "https://mcp.example.com")

    jwks_url = "https://sso.example.com/realms/redhat-external/protocol/openid-connect/certs"

    # Simulate: first response has no jwks_uri, second has it
    first_response = MagicMock()
    first_response.raise_for_status = MagicMock()
    first_response.json.return_value = {}  # no jwks_uri

    second_response = MagicMock()
    second_response.raise_for_status = MagicMock()
    second_response.json.return_value = {"jwks_uri": jwks_url}

    client_mock = MagicMock()
    client_mock.__enter__ = MagicMock(return_value=client_mock)
    client_mock.__exit__ = MagicMock(return_value=False)
    client_mock.get.side_effect = [first_response, second_response]

    with patch("mcp_rh_auth.provider.httpx.Client", return_value=client_mock):
        result = build_auth_provider(required_scopes=["openid"], audience=["mcp"])

    assert result is not None
    assert client_mock.get.call_count == 2


def test_build_auth_provider_mcp_base_url_bridge(monkeypatch):
    """MCP_BASE_URL is read at call-time inside build_auth_provider (no pre-import side effect)."""
    monkeypatch.setenv("AUTH_SERVER", "https://sso.example.com")
    monkeypatch.setenv("AUTH_ISSUER", "https://sso.example.com/realms/redhat-external")
    monkeypatch.setenv("AUTH_JWKS_URI", "https://sso.example.com/jwks")
    monkeypatch.setenv("MCP_BASE_URL", "https://mcp.example.com")
    monkeypatch.delenv("AUTH_RESOURCE", raising=False)

    result = build_auth_provider(required_scopes=["openid"], audience=["mcp"])
    assert result is not None
    # AnyHttpUrl normalizes by appending a trailing slash; strip it for comparison
    assert str(result.resource_base_url).rstrip("/") == "https://mcp.example.com"
