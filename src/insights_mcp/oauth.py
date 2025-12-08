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

from fastmcp.server.auth.oidc_proxy import OIDCProxy
from fastmcp.server.auth.providers.jwt import JWTVerifier
from fastmcp.server.auth.auth import AccessToken

from insights_mcp.config import SSO_CONFIG_URL, SSO_CLIENT_ID, SSO_CLIENT_SECRET

logger = logging.getLogger("insights_mcp.oauth")


def _init_oauth(self, oauth_enabled=True):
    auth = None
    if oauth_enabled:
        # Simple OIDC based protection with required scope validation
        auth_args = dict(
            config_url=SSO_CONFIG_URL,
            client_id=SSO_CLIENT_ID,
            client_secret=SSO_CLIENT_SECRET,
            base_url="http://localhost:8000",
            # These scopes will be REQUIRED - tokens without all of them will be rejected
            # required_scopes=["openid", "api.console", "id.roles", "api.ocm"]
            required_scopes=["openid", "api.console", "api.ocm"]
        )
        auth = OIDCProxy(**auth_args)
    return auth


# Note: approach 1: using custom scope token verifier
# TODO: Try this out to see if it works
# ================================
# Custom scope token verifier
# ================================
class CustomScopeTokenVerifier(JWTVerifier):
    """
    Custom token verifier with advanced scope validation logic.

    This verifier extends JWTVerifier to add custom scope validation
    beyond the simple required_scopes check.
    """

    async def verify_token(self, token: str) -> AccessToken | None:
        """Verify token and perform custom scope validation."""
        print("===== 1111 ===== CustomScopeTokenVerifier.verify_token be called.")
        print("===== 1111 ===== token: ", token)
        logger.debug("===== 1111 ===== CustomScopeTokenVerifier.verify_token be called.")
        # First do the standard JWT verification
        access_token = await super().verify_token(token)

        if not access_token:
            return None

        # Now perform custom scope validation
        if not self._validate_custom_scopes(access_token):
            logger.warning(
                "Custom scope validation failed for client %s with scopes %s",
                access_token.client_id,
                access_token.scopes
            )
            return None

        logger.info(
            "Custom scope validation passed for client %s with scopes %s",
            access_token.client_id,
            access_token.scopes
        )

        return access_token

    def _validate_custom_scopes(self, access_token: AccessToken) -> bool:
        """
        Custom scope validation logic.

        Access the user's scopes via access_token.scopes and claims via access_token.claims
        Implement your business logic here.
        """
        user_scopes = set(access_token.scopes)
        user_claims = access_token.claims
        logger.debug(f"User scopes: {user_scopes}")
        logger.debug(f"User claims: {user_claims}")

        # # Example 1: Require at least one of several scopes
        # admin_scopes = {"api.admin", "api.console.admin"}
        # if not user_scopes.intersection(admin_scopes):
        #     self.logger.debug("User lacks required admin scopes")
        #     # Uncomment to enforce: return False

        # Example 2: Check role claims from Red Hat SSO
        user_roles = user_claims.get("realm_access", {}).get("roles", [])
        logger.debug(f"User roles: {user_roles}")

        # if "insights-admin" not in user_roles:
        #     self.logger.debug("User lacks insights-admin role")
        #     # Uncomment to enforce: return False

        # Example 3: Validate organization access
        org_id = user_claims.get("org_id")
        logger.debug(f"User org_id: {org_id}")
        # if not org_id:
        #     self.logger.debug("User missing org_id claim")
        #     # Uncomment to enforce: return False

        # Example 4: Time-based restrictions
        user_groups = user_claims.get("groups", [])
        logger.debug(f"User groups: {user_groups}")
        # if "beta-users" in user_groups:
        #     self.logger.info("Beta user detected - allowing access")

        # All validations passed
        return True


def _init_oauth_with_custom_verifier(self, oauth_enabled=True):
    """Alternative init function using custom token verifier."""
    auth = None
    if oauth_enabled:
        # Create custom token verifier with advanced scope validation
        custom_verifier = CustomScopeTokenVerifier(
            jwks_uri="https://sso.redhat.com/auth/realms/redhat-external/protocol/openid_connect/certs",
            issuer="https://sso.redhat.com/auth/realms/redhat-external",
            audience=None,  # Red Hat SSO doesn't always set audience
            required_scopes=["openid", "api.console"],  # Basic required scopes
        )

        # Simple OIDC proxy with custom verifier
        auth_args = dict(
            config_url="https://sso.redhat.com/auth/realms/redhat-external/.well-known/openid-configuration",
            client_id=os.getenv("FASTMCP_SERVER_AUTH_SSO_CLIENT_ID") or FASTMCP_SERVER_AUTH_SSO_CLIENT_ID,
            client_secret=os.getenv("FASTMCP_SERVER_AUTH_SSO_CLIENT_SECRET") or FASTMCP_SERVER_AUTH_SSO_CLIENT_SECRET,
            base_url="http://localhost:8000",
            token_verifier=custom_verifier,  # Use our custom verifier
        )
        auth = OIDCProxy(**auth_args)
    return auth


# export _init_oauth_with_custom_verifier
# _init_oauth = _init_oauth_with_custom_verifier  # This is the export for the insights_mcp.server.py


# Note: not used yet
# Note: Approach 2: accessing scopes in your MCP tools
# TODO: Note: try this out to see if it works
# ================================
# Example: Accessing scopes in your MCP tools
# ================================
def example_mcp_tool_with_scope_check():
    """
    Example showing how to access user scopes within MCP tools.

    Add this pattern to your MCP tool implementations in InsightsMCP classes.
    """
    from fastmcp.server.dependencies import get_access_token

    # Get the current authenticated user's token
    access_token = get_access_token()

    if not access_token:
        raise ValueError("Authentication required")

    # Access user scopes and claims
    user_scopes = access_token.scopes
    user_claims = access_token.claims
    client_id = access_token.client_id

    # Perform scope-based authorization
    if "api.admin" not in user_scopes:
        raise PermissionError("Admin scope required for this operation")

    # Check Red Hat SSO role claims
    user_roles = user_claims.get("realm_access", {}).get("roles", [])
    if "insights-admin" not in user_roles:
        raise PermissionError("insights-admin role required")

    # Access organization information
    org_id = user_claims.get("org_id")
    if not org_id:
        raise ValueError("Organization ID not found in token")

    print(f"Authorized user {client_id} with scopes {user_scopes} for org {org_id}")

    # Your tool logic here...
    return {"status": "authorized", "org_id": org_id, "scopes": user_scopes}



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
