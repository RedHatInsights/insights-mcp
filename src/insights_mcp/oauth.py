"""
This module contains the Starlette middleware that implemnts OAuth authorization.
"""

import logging
import httpx
import starlette.middleware
import starlette.middleware.base
import starlette.requests
import starlette.responses
import starlette.types


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
