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
import jwt
from authlib.integrations.httpx_client import AsyncOAuth2Client, OAuthError
from authlib.oauth2.rfc6749 import OAuth2Token

from fastmcp.server.auth import AuthProvider
from fastmcp.server.dependencies import get_http_headers, get_access_token, get_http_request

from insights_mcp.config import INSIGHTS_BASE_URL_PROD, INSIGHTS_TOKEN_ENDPOINT_PROD
from . import __version__

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

    async def get_org_id(self) -> str | None:
        """Extract the organization ID from the access token.

        Returns:
            Organization ID (rh-org-id) as a string, or None if not found.
        """
        return None


class InsightsOAuth2Client(InsightsClientBase, AsyncOAuth2Client):
    """HTTP client with traditional OAuth2 authentication for Red Hat Insights APIs.

    This client handles traditional OAuth2 flows without FastMCP proxy integration:
    1. Service account (client credentials) flow - uses client_id + client_secret
    2. Refresh token flow - uses refresh_token for long-lived sessions

    For FastMCP OAuth proxy integration, use InsightsOAuthProxyClient instead.

    Args:
        base_url: Base URL for the Insights API
        client_id: OAuth2 client ID
        client_secret: OAuth2 client secret for service account authentication
        refresh_token: OAuth2 refresh token for user authentication
        proxy_url: Optional proxy URL for requests
        oauth_enabled: Legacy parameter (use InsightsOAuthProxyClient for proxy mode)
        mcp_transport: MCP transport type for error message customization
        token_endpoint: OAuth2 token endpoint URL
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

    async def refresh_auth(self) -> None:
        """Refresh the authentication token."""
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

        await self.refresh_auth()

        return await super().make_request(fn, *args, **kwargs)

    async def decode_token(self) -> dict[str, Any] | None:
        """Decode the JWT access token and return its payload.

        Note: authlib's OAuth2Token does not provide JWT decoding capabilities.
        While authlib.jose.jwt exists, it requires signature verification which
        is not needed here since we're just reading claims. PyJWT is used instead
        as it supports decoding without verification and is already a dependency.

        Returns:
            Decoded token payload as a dictionary, or None if token is not available or invalid.
        """
        await self.refresh_auth()
        if not self.token or "access_token" not in self.token:
            return None
        try:
            # Decode without verification (since we're just reading claims, not validating)
            # In production, you might want to verify the signature
            decoded = jwt.decode(
                self.token["access_token"],
                options={"verify_signature": False},
                algorithms=["RS256"],
            )
            return decoded
        except jwt.DecodeError:
            return None

    async def get_org_id(self) -> str | None:
        """Extract the organization ID from the access token.

        Returns:
            Organization ID (rh-org-id) as a string, or None if not found.
        """
        payload = await self.decode_token()
        if payload:
            return payload.get("rh-org-id")
        return None

    async def get_user_id(self) -> str | None:
        """Extract the user ID from the access token.

        Returns:
            User ID (rh-user-id) as a string, or None if not found.
        """
        payload = await self.decode_token()
        if payload:
            return payload.get("rh-user-id")
        return None

# Done: feat: implent auto token refresh
#    - MCP client - MCP Inspector - on token expire, seems mcp inspector don't do auto token refresh;
#    - MCP client - Cursor - on token expire, token got auto refreshed, so connection got kept;
# Done: feat: handle multi user connection scenarios (test on Stage, get multiple user in Stage env)
#    - tested on Stage, multiple users can connect to the same server, and request with different tokens
# Done: feat: RBAC usage for account missing some permissions (ask user to request additional access)
#    - current test shows models call rbac__get_all_access for access check, which is same as Service Account auth way. so RBAC is working.
# Done: chore: clean up unused code adding by AI
# TODO: feat: distinguish between user and service account connections on server start up (better flag?)
# TODO: Ask for code review/testing from peers
# WIP: feat: test on integeration with each MCP server module
#  * The known works ones are:
#    - get_insights_mcp_version()
#    - rbac__get_all_access()
#    - inventory__list_hosts()
#    - vulnerability__get_cves()
#    - advisor__get_active_rules()
#    - content-sources__list_repositories()
#    - planning__get_upcoming_changes()
#    - rhsm__get_activation_keys() - though return [] data on insights-mcp-xxw-test2 account;
#  * The known not working ones are:
#    - image_builder__get_org_id() - because image build is using client in a specail way; to make this work.
class InsightsOAuthProxyClient(InsightsClientBase, AsyncOAuth2Client):
    """HTTP client for Red Hat Insights APIs using FastMCP OAuth proxy authentication.

    This client is designed to work seamlessly with FastMCP's OAuth proxy middleware,
    extracting authentication tokens from the current MCP request context and using
    them for Insights API calls. It provides comprehensive logging and debugging
    capabilities for OAuth proxy scenarios.

    The client operates by:
    1. Extracting FastMCP JWT tokens from the current request context
    2. Converting them to OAuth2Token format for API authentication
    3. Performing token expiration checking and validation
    4. Providing detailed request/token logging for debugging

    Key features:
    - Automatic token extraction from FastMCP request context
    - Token expiration monitoring and warnings
    - Comprehensive request and token information logging
    - Seamless integration with FastMCP's OAuth proxy middleware
    - Support for Red Hat Insights API authentication patterns

    Args:
        base_url: Base URL for the Insights API (defaults to production)
        proxy_url: Optional HTTP proxy URL for requests
        mcp_transport: MCP transport type for error message customization
        oauth_provider: AuthProvider instance from FastMCP server (optional)

    Note:
        This client is specifically designed for OAuth proxy scenarios where
        authentication is handled by FastMCP middleware. It does not handle
        traditional OAuth2 flows like client credentials or refresh tokens.
    """

    def __init__(  # pylint: disable=too-many-arguments
        self,
        *,
        base_url: str = INSIGHTS_BASE_URL_PROD,
        proxy_url: str | None = None,
        mcp_transport: str | None = None,
        oauth_provider: AuthProvider | None = None,
    ):
        """Initialize the FastMCP OAuth proxy client.

        Note: This client is designed for OAuth proxy scenarios where
        authentication is handled by FastMCP middleware. Traditional OAuth2
        parameters (client_secret, refresh_token) are typically not needed.
        """

        InsightsClientBase.__init__(self, base_url=base_url, proxy_url=proxy_url, mcp_transport=mcp_transport)

        AsyncOAuth2Client.__init__(
            self,
            grant_type="client_credentials",
            token=OAuth2Token({}),
            headers=self.headers,
            proxy=self.proxy_url,
        )

        # Note: this self.token will be reset on each make_request call by the _extract_access_token_from_request method
        self.token = None  # OAuth2Token({})

        self.oauth_provider = oauth_provider
        self.logger = getLogger("InsightsOAuthProxyClient")

    async def refresh_auth(self) -> None:
        """Extract and prepare authentication token from FastMCP request context.

        This method extracts the FastMCP JWT token from the current MCP request
        context using FastMCP's dependency injection system. The token is then
        converted to OAuth2Token format for use with Insights API calls.

        The method:
        1. Extracts FastMCP JWT token from the current request context
        2. Validates the token is present and accessible
        3. Converts the token to OAuth2Token format for API authentication
        4. Logs token metadata for debugging purposes

        Raises:
            ValueError: If no access token is found in the request context

        Note:
            This method relies on FastMCP's get_access_token() dependency to
            retrieve the authenticated token from the current request scope.
        """
        self.logger.debug("Starting OAuth proxy token exchange")

        # Important: Reset the token to None, to avoid using the previous token
        self.token = None

        # Get access_token from fastmcp request context
        await self._extract_access_token_from_request()
        if not self.token:
            self.logger.error("No access token found in request")
            raise ValueError(self.no_auth_error(ValueError("No access token in request")))

        # # Get access_token from fastmcp request context
        # access_token = await self._extract_access_token_from_request()
        # if not access_token:
        #     self.logger.error("No access token found in request")
        #     raise ValueError(self.no_auth_error(ValueError("No access token in request")))

        self.logger.debug("Successfully retrived SSO token for Insights API authentication")

    async def log_request_and_token_info(self, operation_name: str) -> dict[str, Any]:
        """Log comprehensive token and request information for debugging OAuth proxy operations.

        Provides detailed logging and analysis of the current authentication state,
        including token metadata, request headers, Red Hat SSO claims, and token
        expiration status. This method is essential for debugging OAuth proxy
        authentication issues and monitoring token health.

        Logging includes:
        1. Request headers (with sensitive data masked for security)
        2. OAuth2Token metadata (client_id, scopes, expiration)
        3. Red Hat SSO claims (org_id, account_id, roles, etc.)
        4. Token expiration analysis and warnings
        5. Organizational context for request processing

        Args:
            operation_name: Description of the operation being performed
                          (e.g., "GET /api/vulnerability/v1/cves")

        Returns:
            dict: Comprehensive information dictionary containing:
                - operation_name: The operation being performed
                - request_headers: HTTP headers (sensitive data masked)
                - access_token_info: Token metadata and expiration info
                - redhat_sso_claims: Extracted Red Hat SSO user/org claims

        Note:
            Sensitive information like authorization headers are masked in logs
            for security. The method never raises exceptions to avoid disrupting
            the main request flow, logging warnings for any extraction failures.
        """
        info = {
            "operation_name": operation_name,
            "request_headers": {},
            "access_token_info": {},
            "redhat_sso_claims": {},
            "enhanced_client_debug": {},
        }

        self.logger.info("=== OAuth Proxy Request: %s ===", operation_name)

        # 1. Extract and log request headers
        try:
            request_headers = get_http_headers()
            info["request_headers"] = {}

            self.logger.info("Request headers received:")
            for header_name, header_value in request_headers.items():
                # Security: mask sensitive headers but keep them in debug info
                if header_name.lower() in ['authorization', 'x-api-key', 'bearer']:
                    if len(header_value) > 20:
                        masked_value = f"{header_value[:10]}...{header_value[-6:]}"
                    else:
                        masked_value = "***MASKED***"
                    self.logger.info("  %s: %s", header_name, masked_value)
                    info["request_headers"][header_name] = masked_value
                else:
                    self.logger.info("  %s: %s", header_name, header_value)
                    info["request_headers"][header_name] = header_value

        except Exception as e:
            self.logger.warning("Failed to get request headers: %s", e)
            info["request_headers"]["error"] = str(e)

        # 2. Extract access token from the current token
        try:
            access_token = self.token
            if access_token:
                info["access_token_info"] = {
                    "client_id": access_token.get("client_id"),
                    "scopes": access_token.get("scopes"),
                    "expires_at": access_token.get("expires_at"),
                    "token_length": len(access_token.get("access_token")),
                }

                self.logger.info("FastMCP Access token extracted:")
                self.logger.info("  Client ID: %s", access_token.get("client_id"))
                self.logger.info("  Scopes: %s", access_token.get("scopes"))
                self.logger.info("  Expires at: %s", access_token.get("expires_at"))

                # 3. Extract Red Hat SSO claims if available
                claims = access_token.get("claims")
                if claims:
                    claims_dict = {
                        "issuer": claims.get('iss'),
                        "subject": claims.get('sub'),
                        "org_id": claims.get('org_id'),
                        "account_id": claims.get('account_id'),
                        "username": claims.get('preferred_username'),
                        "email": claims.get('email'),
                        "realm_roles": claims.get('realm_access', {}).get('roles', []),
                        "resource_access": list(claims.get('resource_access', {}).keys()),
                        "groups": claims.get('groups', []),
                    }
                    info["redhat_sso_claims"] = claims_dict

                    self.logger.info("Red Hat SSO claims:")
                    for key, value in claims_dict.items():
                        if value:  # Only log non-empty values
                            self.logger.info("  %s: %s", key, value)

            else:
                self.logger.warning("No access token found in request")
                info["access_token_info"]["error"] = "No token found"

        except Exception as e:
            self.logger.error("Failed to extract access token: %s", e)
            info["access_token_info"]["error"] = str(e)


        self.logger.debug("OAuth proxy request info: %s", info)
        self.logger.info("=== End OAuth Proxy Request Logging ===")
        return info

    async def make_request(self, fn, *args, **kwargs) -> dict[str, Any] | str:
        """Execute HTTP request with FastMCP OAuth proxy authentication and logging.

        This method orchestrates the complete request lifecycle for OAuth proxy scenarios:
        1. Resets any previous token state to ensure clean token extraction
        2. Performs token extraction and authentication setup via refresh_auth()
        3. Logs comprehensive request and token information for debugging
        4. Executes the actual HTTP request with proper authentication headers
        5. Provides token expiration monitoring and warnings

        Args:
            fn: HTTP method function to call (e.g., self.get, self.post)
            *args: Positional arguments for the HTTP method
            **kwargs: Keyword arguments for the HTTP method

        Returns:
            JSON response data as dict, plain text as str, or error information

        Raises:
            ValueError: If token extraction or authentication setup fails
            httpx.HTTPStatusError: If the API request fails with HTTP error
            Exception: For other request-related failures

        Note:
            Each request starts with a clean token state to ensure proper
            token extraction from the current MCP request context.
        """
        # Generate operation description for logging
        method_name = getattr(fn, '__name__', 'unknown_method')
        url = kwargs.get('url', args[0] if args else 'unknown_url')
        operation_name = f"{method_name.upper()} {url}"

        # Always perform token exchange for proxy clients
        try:
            await self.refresh_auth()
            self.logger.debug("Token exchange completed successfully for %s", operation_name)
        except Exception as e:
            self.logger.error("Token exchange failed for %s: %s", operation_name, e)
            raise

        # Log comprehensive request and token information
        try:
            request_info = await self.log_request_and_token_info(operation_name)

            # Extract useful information for request processing
            org_id = request_info.get("redhat_sso_claims", {}).get("org_id")
            if org_id:
                self.logger.info("Processing request for Red Hat organization: %s", org_id)

            # Check token freshness for security-sensitive operations
            token_info = request_info.get("access_token_info", {})
            if token_info.get("expires_at"):
                import time
                current_time = int(time.time())
                expires_at = token_info["expires_at"]
                if expires_at < current_time:
                    self.logger.warning("Access token has expired (expires_at: %s, current: %s)",
                                      expires_at, current_time)
                elif (expires_at - current_time) < 300:  # Less than 5 minutes remaining
                    self.logger.info("Access token expires soon (in %d seconds)", expires_at - current_time)
                else:
                    self.logger.info("Access token is valid (expires_at: %s, current: %s), expire in %d seconds",
                                      expires_at, current_time, expires_at - current_time)

        except Exception as e:
            self.logger.warning("Failed to log request information: %s", e)

        # Execute the actual HTTP request
        try:
            self.logger.info("Executing %s request", operation_name)
            result = await super().make_request(fn, *args, **kwargs)
            self.logger.info("Successfully completed %s request", operation_name)
            return result

        except Exception as e:
            self.logger.error("HTTP request failed for %s: %s", operation_name, e)
            raise

    async def _extract_access_token_from_request(self) -> str | None:
        """Extract FastMCP access token from the current MCP request context.

        Retrieves the authenticated token from FastMCP's dependency injection system
        and converts it to the appropriate format for OAuth2 API calls. The method
        also stores token metadata in the OAuth2Token format for request authentication.

        Process:
        1. Uses get_access_token() to retrieve AccessToken from FastMCP dependencies
        2. Extracts the JWT token string from the AccessToken object
        3. Converts AccessToken metadata to OAuth2Token format
        4. Stores the OAuth2Token for use in API authentication
        5. Logs token metadata for debugging purposes

        Returns:
            str: The FastMCP JWT token string if successfully extracted
            None: If no token is available in the request context

        Note:
            This method relies on FastMCP's request-scoped dependency injection.
            It will return None if called outside of an MCP request context or
            if no authenticated token is available. The method does not raise
            exceptions to allow graceful handling of missing tokens.
        """
        self.logger.debug("Extracting FastMCP access token from request")

        # Method 1: Get AccessToken object from FastMCP dependencies (preferred)
        try:
            access_token_obj = get_access_token()
            if access_token_obj and access_token_obj.token:
                token_length = len(access_token_obj.token)
                self.logger.debug(
                    "Successfully retrieved access token from FastMCP dependencies (length: %d)",
                    token_length
                )

                # Log token metadata for debugging
                self.logger.debug("Token metadata: client_id=%s, scopes=%s, expires_at=%s",
                                access_token_obj.client_id,
                                access_token_obj.scopes,
                                access_token_obj.expires_at)

                access_token_dict = access_token_obj.model_dump()
                self.logger.debug("AccessToken dictionary: %s", access_token_dict)
                # Customize the AccessToken dictionary for OAuth2Token
                access_token_dict["access_token"] = access_token_obj.token

                # Store the AccessToken object for later use in the make_request lifecycle
                self.token = OAuth2Token(access_token_dict)
                self.logger.debug("self.token OAuth2Token object stored: %s", self.token)

                return self.token
            else:
                self.logger.debug("AccessToken object found but no token present")

        except Exception as e:
            self.logger.debug("Failed to get access token from FastMCP dependencies: %s", e)

    # TODO: to test with image_builder__get_org_id() mcp call
    async def get_org_id(self) -> str | None:
        """Extract Red Hat organization ID from the current request token.

        Provides compatibility with other Insights client implementations by extracting
        the organization ID required for Red Hat multi-tenant services. This method
        ensures the token is properly extracted from the current request context before
        attempting to retrieve the organization ID.

        The method uses a two-tier approach for maximum compatibility:
        1. Primary: Extracts org_id from pre-parsed token claims (most efficient)
        2. Fallback: Decodes the JWT token directly to access org_id claims

        Returns:
            str: Red Hat organization ID if found in the authentication token
            None: This method raises ValueError instead of returning None

        Raises:
            ValueError: If no access token is available in the request context
            ValueError: If org_id is not found in the token claims

        Note:
            The organization ID is essential for Red Hat multi-tenant services to ensure
            users only access resources within their organization. This method implements
            the same interface as other Insights client classes for consistency.
        """
        try:
            # Retrive token on this request
            await self.refresh_auth()
            if not self.token:
                self.logger.error("No access token found for this `get_org_id()` request")
                raise ValueError(self.no_auth_error(ValueError("No access token in request")))

            # Main method: Try to get org_id from token claims directly
            claims = self.token.get("claims")
            if claims:
                org_id = claims.get("org_id") or claims.get("rh-org-id")
                if org_id:
                    return org_id

            # Fallback method: Decode JWT token to get org_id
            payload = jwt.decode(
                self.token.get("access_token"),
                options={"verify_signature": False, "verify_exp": False},
                algorithms=["HS256", "RS256"]
            )
            claims = payload.get('claims')
            if claims:
                return claims.get("org_id") or claims.get("rh-org-id")

        except Exception as e:
            self.logger.error("No org_id found in token claims")
            raise ValueError(self.no_auth_error(ValueError("No org_id in token claims")))


# Example usage patterns for the different client types:
#
# 1. FastMCP OAuth Proxy (recommended for MCP tools):
#    client = InsightsOAuthProxyClient(
#        base_url="https://console.redhat.com",
#        mcp_transport="http"
#    )
#
# 2. Service Account Authentication:
#    client = InsightsOAuth2Client(
#        base_url="https://console.redhat.com",
#        client_id="my-service-account",
#        client_secret="my-secret",
#        oauth_enabled=False
#    )
#
# 3. High-level client (auto-selects based on parameters):
#    # For FastMCP proxy:
#    client = InsightsClient(
#        api_path="api/insights/v1",
#        oauth_enabled=True
#    )
#    # For service account:
#    client = InsightsClient(
#        api_path="api/insights/v1",
#        client_secret="my-secret"
#    )


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
        oauth_provider: AuthProvider instance for OAuth authentication
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
        oauth_provider: AuthProvider | None = None,
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
        self.oauth_provider = oauth_provider
        self.mcp_transport = mcp_transport
        self.token_endpoint = token_endpoint

        self.client_noauth = InsightsNoauthClient(base_url=base_url, proxy_url=proxy_url, mcp_transport=mcp_transport)
        self.client = self.client_noauth

        if oauth_enabled:
            # Use dedicated OAuth proxy client for FastMCP integration
            self.client = InsightsOAuthProxyClient(
                base_url=base_url,
                proxy_url=proxy_url,
                mcp_transport=mcp_transport,
                oauth_provider=oauth_provider,
            )
        elif refresh_token or client_secret:
            # Use traditional OAuth2 client for service account/refresh token flows
            self.client = InsightsOAuth2Client(
                base_url=base_url,
                client_id=client_id,
                client_secret=client_secret,
                refresh_token=refresh_token,
                proxy_url=proxy_url,
                oauth_enabled=False,  # Explicitly disable for traditional flow
                mcp_transport=mcp_transport,
                token_endpoint=token_endpoint,
            )

        # merge headers with client headers
        if headers:
            self.client.headers.update(headers)

    async def get_org_id(self) -> str | None:
        """Get the organization ID from the user."""

        return await self.client.get_org_id()

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
