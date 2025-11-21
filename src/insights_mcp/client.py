"""Red Hat Insights API client implementation.

This module provides HTTP client classes for interacting with Red Hat Insights APIs.
It supports both authenticated and unauthenticated requests, with OAuth2 authentication
handling for service account and refresh token-based flows.

Classes:
    InsightsClientBase: Base HTTP client with common functionality
    InsightsNoauthClient: Client for unauthenticated requests
    InsightsOAuth2Client: Client with OAuth2 authentication support
    InsightsClient: High-level client that automatically selects auth method
"""

import gzip
import json as json_lib
from logging import getLogger
from typing import Any

import httpx
from authlib.integrations.httpx_client import AsyncOAuth2Client, OAuthError
from authlib.oauth2.rfc6749 import OAuth2Token
from fastmcp.server.dependencies import get_http_headers

from . import __version__

INSIGHTS_BASE_URL_PROD = "https://console.redhat.com"
INSIGHTS_TOKEN_ENDPOINT_PROD = "https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token"
USER_AGENT = f"insights-mcp/{__version__}"


class InsightsClientBase(httpx.AsyncClient):
    """Base HTTP client for Red Hat Insights APIs.

    Provides common functionality for making HTTP requests to Insights APIs,
    including error handling, logging, and proxy support.

    Args:
        base_url: Base URL for the Insights API
        proxy_url: Optional proxy URL for requests
        mcp_transport: MCP transport type for error message customization
    """

    def __init__(
        self,
        base_url: str,
        proxy_url: str | None = None,
        mcp_transport: str | None = None,
    ):
        super().__init__(
            headers={"User-Agent": USER_AGENT, "Content-Type": "application/json"},
            proxy=proxy_url,
        )
        self.insights_base_url = base_url
        self.proxy_url = proxy_url
        self.mcp_transport = mcp_transport
        self.logger = getLogger("InsightsClientBase")

    async def make_request(self, fn, *args, **kwargs) -> dict[str, Any] | str:
        """Make an HTTP request with error handling.

        Args:
            fn: HTTP method function to call (e.g., self.get, self.post)
            *args: Positional arguments for the HTTP method
            **kwargs: Keyword arguments for the HTTP method

        Returns:
            JSON response data or error information
        """
        try:
            self.logger.debug(
                "Making %s request to %s with data %s",
                fn.__name__,
                kwargs.get("url"),
                kwargs.get("json"),
            )
            response = await fn(*args, **kwargs)
            response.raise_for_status()

            # Handle gzipped responses
            content = response.content
            if response.headers.get("content-encoding") == "gzip":
                self.logger.debug("Response is gzipped, decompressing...")
                try:
                    content = gzip.decompress(content)
                except gzip.BadGzipFile as e:
                    # for some reason it says to be gzipped but isn't
                    self.logger.debug("Failed to decompress gzipped content: %s; continuing with original content", e)
                    # Fall back to original content

            # Try to parse as JSON
            try:
                return json_lib.loads(content.decode("utf-8"))
            except json_lib.JSONDecodeError:
                # Return as string if not valid JSON
                return content.decode("utf-8")

        except json_lib.JSONDecodeError as e:
            # failed to decode JSON, return raw content
            self.logger.debug("JSONDecodeError: %s", e)
            return response.content.decode("utf-8")
        except httpx.HTTPStatusError as e:
            content = self.get_error_message(e)
            return content
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return {"Unhandled error": str(exc)}

    def get_error_message(self, e: httpx.HTTPStatusError) -> str:
        """Generate appropriate error message based on HTTP status code.

        Args:
            e: HTTP status error exception

        Returns:
            User-friendly error message
        """
        match e.response.status_code:
            case httpx.codes.UNAUTHORIZED:
                return self.no_auth_error(e)
            case httpx.codes.FORBIDDEN:
                return self.no_rbac_error(e)
            case _:
                return (
                    f"Unexpected HTTP status code: {e.response.status_code}, "
                    f"content: {e.response.content.decode('utf-8')}"
                )

    def no_auth_error(self, e: httpx.HTTPStatusError | ValueError) -> str:
        """Generate authentication error message based on transport type.

        Args:
            e: HTTP status error or value error exception

        Returns:
            Detailed authentication error message with setup instructions
        """
        base_message = (
            "[INSTRUCTION] There seems to be a problem with the request. "
            "Without asking the user, immediately call get_insights_mcp_version() to check "
            "if we are on the latest release. ALSO call get_all_access() to check "
            "if it's an authentication problem or just missing permissions.\n"
            "ONLY if it is an authentication problem that *also occurs* with get_all_access(), tell the user "
            "that the MCP server setup is not valid! "
            f"The user should go to [{self.insights_base_url}]({self.insights_base_url}) to "
            "Click Settings (⚙️ Gear Icon) ➡ Service Accounts ➡ create a service account and then set the "
        )
        error_message = str(e)
        # strip off "401 Unauthorized"
        # this confuses LLMs
        # just replacing with a nice text which can be found in logs later :-D
        error_message = error_message.replace("401 Unauthorized", "THE request problem")
        error_message = error_message.replace(
            "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/401", "relevant MCP functions"
        )
        if self.mcp_transport in ["sse", "http"]:
            return (
                f"{base_message}header variables `insights-client-id` and "
                "`insights-client-secret` in your request.\n"
                "Here is the direct link for the user's convenience: "
                f"[{self.insights_base_url}/iam/service-accounts]({self.insights_base_url}/iam/service-accounts) "
                "Come up with a detailed description of this for the user. "
                "Only describe this, don't expose details about the tool function itself. "
                f"Don't proceed with the request before this is fixed. {error_message}"
            )

        return (
            f"{base_message}`INSIGHTS_CLIENT_ID` and `INSIGHTS_CLIENT_SECRET` "
            "in your mcp.json config.\n"
            "Here is the direct link for the user's convenience: "
            f"[{self.insights_base_url}/iam/service-accounts]({self.insights_base_url}/iam/service-accounts) "
            "Come up with a detailed description of this for the user. "
            "Only describe this, don't expose details about the tool function itself. "
            f"Don't proceed with the request before this is fixed. {error_message}"
        )

    def no_rbac_error(self, e: httpx.HTTPStatusError) -> str:
        """Generate RBAC/permissions error message.

        Args:
            e: HTTP status error exception

        Returns:
            Detailed permissions error message with access request instructions
        """
        return (
            f"[INSTRUCTION] Use get_insights_mcp_version() to check if we are on the latest release. "
            "Also use rbac__get_all_access() to list all current permissions"
            " and help the user find out which permissions might be missing."
            f"Then the user should go to [{self.insights_base_url}/iam/user-access/overview]"
            f"({self.insights_base_url}/iam/user-access/overview) to check their RBAC permissions and roles."
            " They may need to request additional access or have an "
            "administrator grant them the necessary permissions for this resource. The user is authenticated but "
            "lacks the required permissions to access this resource.\n"
            "Come up with a detailed description of this for the user. "
            "Only describe this, don't expose details about the tool function itself. "
            f"Don't proceed with the request before this is fixed. Error: {str(e)}."
        )


class InsightsNoauthClient(InsightsClientBase):
    """HTTP client for unauthenticated requests to Red Hat Insights APIs.

    Args:
        base_url: Base URL for the Insights API
        proxy_url: Optional proxy URL for requests
        mcp_transport: MCP transport type for error message customization
    """

    def __init__(
        self,
        base_url: str = INSIGHTS_BASE_URL_PROD,
        proxy_url: str | None = None,
        mcp_transport: str | None = None,
    ):
        super().__init__(base_url=base_url, proxy_url=proxy_url, mcp_transport=mcp_transport)


class InsightsOAuth2Client(InsightsClientBase, AsyncOAuth2Client):
    """HTTP client with OAuth2 authentication for Red Hat Insights APIs.

    Supports both service account (client credentials) and refresh token flows.
    Automatically handles token refresh when tokens expire.

    Args:
        base_url: Base URL for the Insights API
        client_id: OAuth2 client ID
        client_secret: OAuth2 client secret
        refresh_token: OAuth2 refresh token
        proxy_url: Optional proxy URL for requests
        oauth_enabled: Whether OAuth middleware is handling authentication
        mcp_transport: MCP transport type for error message customization
    """

    def __init__(  # pylint: disable=too-many-arguments
        self,
        *,
        base_url: str = INSIGHTS_BASE_URL_PROD,
        client_id: str | None = "rhsm-api",
        client_secret: str | None = None,
        refresh_token: str | None = None,
        proxy_url: str | None = None,
        oauth_enabled: bool = False,
        mcp_transport: str | None = None,
        token_endpoint: str = INSIGHTS_TOKEN_ENDPOINT_PROD,
    ):
        InsightsClientBase.__init__(self, base_url=base_url, proxy_url=proxy_url, mcp_transport=mcp_transport)
        token_dict = {"refresh_token": refresh_token} if refresh_token else {}
        token = OAuth2Token(token_dict)
        grant_type = "refresh_token" if refresh_token else "client_credentials"

        AsyncOAuth2Client.__init__(
            self,
            client_id=client_id,
            client_secret=client_secret,
            grant_type=grant_type,
            token=token,
            token_endpoint=token_endpoint,
            headers=self.headers,
            proxy=self.proxy_url,
        )
        self.oauth_enabled = oauth_enabled

    async def make_request(self, fn, *args, **kwargs) -> dict[str, Any] | str:
        """Make an HTTP request with OAuth2 token management.

        Handles token refresh when needed and supports OAuth middleware.

        Args:
            fn: HTTP method function to call
            *args: Positional arguments for the HTTP method
            **kwargs: Keyword arguments for the HTTP method

        Returns:
            JSON response data or error information
        """
        if not self.oauth_enabled and self.refresh_token is None and self.client_secret is None:
            return self.no_auth_error(ValueError("Client not authenticated"))

        if self.oauth_enabled:  # TODO: unify client oauth and oauth middleware
            self.logger.info("OAuth is enabled, skipping token management")
            caller_headers_auth = get_http_headers().get("authorization")
            if caller_headers_auth:
                # If the request is authenticated, use the caller's authorization header
                # This is useful for OAuth flows where the client is already authenticated
                self.headers["authorization"] = caller_headers_auth
        elif "access_token" not in self.token or self.token.is_expired():
            self.logger.info("Token is expired, refreshing token")
            try:
                if "refresh_token" in self.token:
                    await self.refresh_token()
                else:
                    await self.fetch_token()
            except OAuthError as e:
                raise ValueError(self.no_auth_error(e)) from e
        return await super().make_request(fn, *args, **kwargs)


class InsightsClient:  # pylint: disable=too-many-instance-attributes
    """High-level HTTP client for Red Hat Insights APIs.

    Automatically selects between authenticated and unauthenticated clients
    based on the provided credentials. Provides convenient methods for
    common HTTP operations.

    Args:
        api_path: API path segment to append to base URL
        base_url: Base URL for the Insights API
        client_id: OAuth2 client ID
        client_secret: OAuth2 client secret
        refresh_token: OAuth2 refresh token
        headers: Additional HTTP headers
        proxy_url: Optional proxy URL for requests
        oauth_enabled: Whether OAuth middleware is handling authentication
        mcp_transport: MCP transport type for error message customization
    """

    def __init__(  # pylint: disable=too-many-arguments
        self,
        *,
        api_path: str,
        base_url: str = INSIGHTS_BASE_URL_PROD,
        client_id: str | None = "rhsm-api",
        client_secret: str | None = None,
        refresh_token: str | None = None,
        headers: dict[str, str] | None = None,
        proxy_url: str | None = None,
        oauth_enabled: bool = False,
        mcp_transport: str | None = None,  # TODO: get rid of mcp_transport in client
        token_endpoint: str = INSIGHTS_TOKEN_ENDPOINT_PROD,
    ):
        self.logger = getLogger("InsightsClient")
        self.logger.info("Initializing insights client")
        # NOTE: probably we don't need to set all these variables,
        # but set them before refactor of ImageBuilderMCP
        self.insights_base_url = base_url
        self.api_path = api_path
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.headers = headers
        self.proxy_url = proxy_url
        self.oauth_enabled = oauth_enabled
        self.mcp_transport = mcp_transport
        self.token_endpoint = token_endpoint

        self.client_noauth = InsightsNoauthClient(base_url=base_url, proxy_url=proxy_url, mcp_transport=mcp_transport)
        self.client = self.client_noauth

        if oauth_enabled or refresh_token or client_secret:
            self.client = InsightsOAuth2Client(
                # pylint: disable=duplicate-code
                base_url=base_url,
                client_id=client_id,
                client_secret=client_secret,
                refresh_token=refresh_token,
                proxy_url=proxy_url,
                oauth_enabled=oauth_enabled,
                mcp_transport=mcp_transport,
                token_endpoint=token_endpoint,
            )

        # merge headers with client headers
        if headers:
            self.client.headers.update(headers)

    async def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        noauth: bool = False,
        **kwargs,
    ) -> dict[str, Any] | str:
        """Make a GET request to the API.

        Args:
            endpoint: API endpoint to call
            params: Query parameters for the request
            noauth: Whether to make an unauthenticated request
            **kwargs: Additional arguments for the HTTP request

        Returns:
            JSON response data or error information
        """
        client = self.client_noauth if noauth else self.client
        url = f"{self.insights_base_url}/{self.api_path}/{endpoint}"
        return await client.make_request(client.get, url=url, params=params, **kwargs)

    async def post(
        self,
        endpoint: str,
        json: dict[str, Any] | None = None,
        noauth: bool = False,
        **kwargs,
    ) -> dict[str, Any] | str:
        """Make a POST request to the API.

        Args:
            endpoint: API endpoint to call
            json: JSON data for the request body
            noauth: Whether to make an unauthenticated request
            **kwargs: Additional arguments for the HTTP request

        Returns:
            JSON response data or error information
        """
        client = self.client_noauth if noauth else self.client
        url = f"{self.insights_base_url}/{self.api_path}/{endpoint}"
        return await client.make_request(client.post, url=url, json=json, **kwargs)

    async def put(
        self,
        endpoint: str,
        json: dict[str, Any] | None = None,
        noauth: bool = False,
        **kwargs,
    ) -> dict[str, Any] | str:
        """Make a PUT request to the API.

        Args:
            endpoint: API endpoint to call
            json: JSON data for the request body
            noauth: Whether to make an unauthenticated request
            **kwargs: Additional arguments for the HTTP request

        Returns:
            JSON response data or error information
        """
        client = self.client_noauth if noauth else self.client
        url = f"{self.insights_base_url}/{self.api_path}/{endpoint}"
        return await client.make_request(client.put, url=url, json=json, **kwargs)
