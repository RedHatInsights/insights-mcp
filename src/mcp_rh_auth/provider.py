"""OAuth/JWT auth provider builder for FastMCP servers using Red Hat SSO."""

from __future__ import annotations

import logging
import os
from typing import Any, cast
from urllib.parse import urljoin

import httpx
from fastmcp.server.auth import RemoteAuthProvider
from fastmcp.server.auth.providers.jwt import JWTVerifier
from pydantic import AnyHttpUrl

from mcp_rh_auth.http import get_httpx_async_client, httpx_verify_setting

logger = logging.getLogger(__name__)

AUTHORIZATION_SERVER_METADATA_PATH = "/.well-known/oauth-authorization-server"
OPENID_CONFIGURATION_PATH = "/.well-known/openid-configuration"

_DEFAULT_SCOPES = ["api.graphql"]


def _authorization_server_metadata_urls(auth_server: str) -> list[str]:
    base = auth_server.rstrip("/") + "/"
    return [
        urljoin(base, AUTHORIZATION_SERVER_METADATA_PATH.lstrip("/")),
        urljoin(base, OPENID_CONFIGURATION_PATH.lstrip("/")),
    ]


def _fetch_authorization_server_metadata(auth_server: str) -> dict[str, Any]:
    errors: list[str] = []
    for metadata_url in _authorization_server_metadata_urls(auth_server):
        try:
            with httpx.Client(timeout=30.0, verify=httpx_verify_setting()) as client:
                response = client.get(metadata_url)
            response.raise_for_status()
            metadata = cast(dict[str, Any], response.json())
            if metadata.get("jwks_uri"):
                return metadata
            errors.append(f"{metadata_url}: missing jwks_uri")
        except (httpx.HTTPError, ValueError) as exc:
            errors.append(f"{metadata_url}: {exc}")

    raise ValueError(f"Could not load jwks_uri from AUTH_SERVER ({auth_server!r}); tried {', '.join(errors)}.")


def _resolve_jwt_verifier_config(auth_server: str) -> tuple[str, str]:
    auth_issuer = os.getenv("AUTH_ISSUER", "")
    if not auth_issuer:
        raise ValueError("AUTH_ISSUER is required")
    auth_jwks_uri = os.getenv("AUTH_JWKS_URI", "")
    if auth_jwks_uri:
        return auth_issuer, auth_jwks_uri
    metadata = _fetch_authorization_server_metadata(auth_server)
    return auth_issuer, metadata["jwks_uri"]


def _resolve_scopes(env_var: str, explicit: list[str] | None) -> list[str]:
    if explicit is not None:
        return explicit
    env_val = os.getenv(env_var)
    if env_val:
        return [s.strip() for s in env_val.split(",") if s.strip()]
    return _DEFAULT_SCOPES


def _resolve_mcp_base_url() -> str:
    """Resolve the MCP server base URL from env vars.

    Priority: MCP_BASE_URL > AUTH_RESOURCE (strip /mcp suffix) > empty string.
    This replaces the pre-import os.environ hack in server.py: instead of setting
    AUTH_RESOURCE before importing the auth module, callers just set MCP_BASE_URL.
    """
    mcp_base_url = os.getenv("MCP_BASE_URL", "").rstrip("/")
    if mcp_base_url:
        return mcp_base_url
    auth_resource = os.getenv("AUTH_RESOURCE", "").rstrip("/")
    if auth_resource.endswith("/mcp"):
        return auth_resource[: -len("/mcp")]
    return auth_resource


def build_auth_provider(
    required_scopes: list[str] | None = None,
    audience: list[str] | None = None,
) -> RemoteAuthProvider | None:
    """Configure OAuth via mcp-auth with SSO JWT verification.

    Returns None when AUTH_SERVER is unset (stdio / no-auth mode).
    """
    auth_server = os.getenv("AUTH_SERVER", "")
    if not auth_server:
        logger.error("AUTH_SERVER is required")
        return None

    resolved_scopes = _resolve_scopes("AUTH_SCOPES", required_scopes)
    resolved_audience = _resolve_scopes("AUTH_AUDIENCE", audience)

    issuer, jwks_uri = _resolve_jwt_verifier_config(auth_server)
    verifier = JWTVerifier(
        jwks_uri=jwks_uri,
        issuer=issuer,
        audience=resolved_audience,
        required_scopes=resolved_scopes,
        http_client=get_httpx_async_client(),
    )

    mcp_base_url = _resolve_mcp_base_url()
    return RemoteAuthProvider(
        token_verifier=verifier,
        authorization_servers=[AnyHttpUrl(auth_server)],
        base_url=mcp_base_url,
        resource_base_url=mcp_base_url,
    )
