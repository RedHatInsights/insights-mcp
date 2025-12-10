"""
This module contains the Starlette middleware that implemnts OAuth authorization.
"""

import logging
import os

import httpx
import starlette.middleware
import starlette.middleware.base
import starlette.requests
import starlette.responses
import starlette.types

from fastmcp.server.auth import AuthProvider
from fastmcp.server.auth.oidc_proxy import OIDCProxy
from insights_mcp import config

logger = logging.getLogger("insights_mcp.oauth")


def init_oauth_provider(
    client_id: str | None = None,
    client_secret: str | None = None,
    mcp_host: str | None = None,
    mcp_port: int | None = None,
) -> AuthProvider | None:
    """Initialize OAuth authentication provider for FastMCP server integration.

    Creates an OIDCProxy instance configured for Red Hat Single Sign-On (RH-SSO)
    authentication. This provider acts as a transparent proxy to the upstream
    Red Hat SSO OIDC Authorization Server, handling Dynamic Client Registration
    and forwarding OAuth flows for MCP clients.

    The provider implements the complete OAuth2/OIDC flow:
    1. Dynamic Client Registration (DCR) for MCP clients
    2. Authorization code flow with PKCE support
    3. Token validation and refresh capabilities
    4. Scope-based access control with required scopes enforcement

    Args:
        client_id: OAuth2 client ID registered with Red Hat SSO.
                  If None, uses SSO_CLIENT_ID from configuration.
        client_secret: OAuth2 client secret for the registered client.
                      If None, uses SSO_CLIENT_SECRET from configuration.
        mcp_host: Hostname where the MCP server will be accessible to clients.
                 Used for OAuth callback URL construction.
        mcp_port: Port where the MCP server will listen for client connections.
                 Used for OAuth callback URL construction.

    Returns:
        AuthProvider: Configured OIDCProxy instance ready for FastMCP integration.
        None: If OAuth authentication is disabled or configuration is invalid.

    Raises:
        ValueError: If required configuration parameters are missing or invalid.
        ConnectionError: If unable to connect to Red Hat SSO configuration endpoint.

    Note:
        The provider enforces these required OAuth scopes:
        - "openid": Standard OIDC identity scope
        - "api.console": Access to Red Hat Console APIs
        - "api.ocm": Access to OpenShift Cluster Manager APIs

        Tokens without ALL required scopes will be rejected during authentication.

    Example:
        ```python
        # Initialize with explicit parameters
        auth_provider = init_oauth_provider(
            client_id="my-sso-client",
            client_secret="my-sso-secret",
            mcp_host="localhost",
            mcp_port=8000
        )

        # Initialize using configuration defaults
        auth_provider = init_oauth_provider()

        # Use with FastMCP server
        mcp_server = FastMCP(
            name="My Insights Server",
            auth=auth_provider
        )
        ```
    """
     # Construct base URL for OAuth callbacks and metadata endpoints
    base_url = (
        f"http://{mcp_host}:{mcp_port}"
        if mcp_host and mcp_port
        else "http://localhost:8000"
    )
    logger.debug("Initializing OAuth provider with base_url: %s", base_url)

    # Configure OIDC proxy with Red Hat SSO settings
    auth_args = {
        "config_url": config.SSO_CONFIG_URL,
        "client_id": client_id or config.SSO_CLIENT_ID,
        "client_secret": client_secret or config.SSO_CLIENT_SECRET,
        "base_url": base_url,
        # Required scopes - tokens missing any of these will be rejected
        "required_scopes": ["openid", "api.console", "api.ocm"],
        "timeout_seconds": config.SSO_OAUTH_TIMEOUT_SECONDS,
    }

    logger.debug("Creating OIDCProxy with config: %s", {
        k: v if k not in ["client_secret"] else "***REDACTED***"
        for k, v in auth_args.items()
    })

    try:
        oauth_provider = OIDCProxy(**auth_args)
        logger.info("Successfully initialized OAuth provider for %s", base_url)
        return oauth_provider
    except Exception as e:
        logger.error("Failed to initialize OAuth provider: %s", e)
        raise


# Not used anymore, to remove later.
class Middleware(starlette.middleware.base.BaseHTTPMiddleware):  # pylint: disable=too-few-public-methods
    """
    This middleware implements the OAuth metadata and registration endpoints that MCP clients
    will try to use when the server responds with a 401 status code.
    """

    def __init__(
        self,
        app: starlette.types.ASGIApp,
        self_url: str,
        oauth_url: str,
        oauth_client: str,
    ):
        """
        Creates a new OAuth middleware.

        Args:
            app (starlette.types.ASGIApp): The starlette application.
            self_url (str): Base URL of the service, as seen by clients.
            oauth_url (str): Base URL of the authorization server.
            oauth_client (str): The client identifier.
        """
        super().__init__(app=app)
        self._self_url = self_url
        self._oauth_url = oauth_url
        self._oauth_client = oauth_client
        self.logger = logging.getLogger("ImageBuilderOAuthMiddleware")

    async def dispatch(
        self,
        request: starlette.requests.Request,
        call_next: starlette.middleware.base.RequestResponseEndpoint,
    ) -> starlette.responses.Response:
        """
        Dispatches the request, calling the OAuth handlers or else the protected application.
        """
        # The OAuth endpoints don't require authentication:
        method = request.method
        path = request.url.path
        if method == "GET" and path == "/.well-known/oauth-protected-resource":
            return await self._resource(request)
        if method == "GET" and path == "/.well-known/oauth-authorization-server":
            return await self._metadata(request)
        if method == "POST" and path == "/oauth/register":
            return await self._register(request)
        if path == "/mcp":
            self.logger.warning("Workaround to skip redirect /mcp to /mcp/")
            # Adapt the path by adding the trailing slash
            # vscode seems to have problems with executing the 307 redirect
            # that the MCP server returns when the path is not ending with a slash.
            request.scope["path"] = "/mcp/"

        # The rest of the endpoints do require authentication. Note that we are not validating the
        # bearer token, just requiring the authorization header, so that the client will receive
        # the 401 response code and trigger the OAuth flow.
        auth = request.headers.get("authorization")
        if auth is None:
            resource_url = f"{self._self_url}/.well-known/oauth-protected-resource"
            return starlette.responses.Response(
                status_code=401,
                headers={
                    "WWW-Authenticate": f'Bearer resource_metadata="{resource_url}"',
                },
            )

        return await call_next(request)

    async def _resource(self, request: starlette.requests.Request) -> starlette.responses.Response:  # pylint: disable=unused-argument
        """
        This method implements the OAuth protected resource endpoint.
        """
        return starlette.responses.JSONResponse(
            content={
                "resource": self._self_url,
                "authorization_servers": [
                    self._self_url,
                ],
                "bearer_methods_supported": [
                    "header",
                ],
                "scopes_supported": [
                    "openid",
                    "api.console",
                    "api.ocm",
                ],
            }
        )

    async def _metadata(self, request: starlette.requests.Request) -> starlette.responses.Response:  # pylint: disable=unused-argument
        """
        This method implements the OAuth metadata endpoint. It gets the metadata from our real authorization
        server, and replaces a few things that are needed to satisfy MCP clients.
        """
        # Get the metadata from the real authorization service:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url=f"{self._oauth_url}/.well-known/oauth-authorization-server",
                    timeout=10,
                )
                response.raise_for_status()
                body = response.json()
        except (httpx.RequestError, httpx.HTTPStatusError):
            return starlette.responses.Response(status_code=503)

        # The MCP clients will want to dynamically register the client, but we don't want that because our
        # authorization server doesn't allow us to do it. So we replace the registration endpoint with our
        # own, where we can return a fake response to make the MCP clients happy.
        body["registration_endpoint"] = f"{self._self_url}/oauth/register"

        # The MCP clients also try to request all the scopes listed in the metadata, but our authorization
        # server returns a lot of scopes, and most of them will be rejected for our client. So we replace
        # that large list with a much smaller list containing only the scopes that we need.
        body["scopes_supported"] = [
            "openid",
            "api.ocm",
        ]

        # Return the modified metadata:
        return starlette.responses.JSONResponse(
            content=body,
        )

    async def _register(self, request: starlette.requests.Request) -> starlette.responses.Response:
        """
        This method implements the OAuth dynamic client registration endpoint. It responds to all requests
        with a fixed client identifier.
        """
        body = await request.json()
        redirect_uris = body.get("redirect_uris", [])
        return starlette.responses.JSONResponse(
            content={
                "client_id": self._oauth_client,
                "redirect_uris": redirect_uris,
            },
        )
