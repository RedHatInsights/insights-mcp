# mcp-rh-auth

MCP OAuth/JWT auth provider for FastMCP servers using Red Hat SSO.

## What it does

Wires a `RemoteAuthProvider` into a FastMCP server that:

- Fetches JWKS from the authorization server's `/.well-known/oauth-authorization-server` (falling back to `/.well-known/openid-configuration`)
- Validates inbound Bearer tokens using `JWTVerifier` (issuer, audience, required scopes)
- Returns `None` when `AUTH_SERVER` is not set — making auth a no-op for stdio / local deployments

## Usage

```python
from mcp_rh_auth import build_auth_provider
from fastmcp import FastMCP

server = FastMCP(
    name="My MCP Server",
    auth=build_auth_provider(
        required_scopes=["openid", "api.myservice"],
        audience=["my-mcp-server"],
    ),
)
```

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `AUTH_SERVER` | Yes (HTTP mode) | OAuth authorization server base URL (e.g. `https://sso.redhat.com`) |
| `AUTH_ISSUER` | Yes (HTTP mode) | JWT issuer claim (e.g. `https://sso.redhat.com/auth/realms/redhat-external`) |
| `MCP_BASE_URL` | Recommended | Public base URL of this MCP server, used as `resource_base_url` in the provider |
| `AUTH_JWKS_URI` | No | Override JWKS endpoint; skips metadata discovery when set |
| `AUTH_SCOPES` | No | Comma-separated required scopes; overridden by `required_scopes` argument |
| `AUTH_AUDIENCE` | No | Comma-separated accepted audiences; overridden by `audience` argument |
| `AUTH_RESOURCE` | No | Fallback resource URL when `MCP_BASE_URL` is not set |
| `SSL_VERIFY` | No | Set to `false` to disable TLS verification (development only) |
| `EXTRA_CA_CERTS` | No | Path to an extra CA bundle (useful on macOS with a corporate proxy) |

When `AUTH_SERVER` is absent, `build_auth_provider` returns `None` and no authentication is enforced — safe for stdio and self-hosted deployments without SSO.

## Using from another project

This package is bundled inside `insights-mcp`. Installing `insights-mcp` from git also makes `mcp_rh_auth` importable, since Python distribution names and import names are independent:

```toml
# pyproject.toml of the consuming project
dependencies = [
    "insights-mcp @ git+https://github.com/RedHatInsights/insights-mcp.git",
]
```

```python
from mcp_rh_auth import build_auth_provider
```
