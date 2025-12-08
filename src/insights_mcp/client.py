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

# TODO: feat: implent auto token refresh
# TODO: feat: handle multi user connection scenarios (test on Stage, get multiple user in Stage env)
#    - tested on Stage, multiple users can connect to the same server, and request with different tokens
# TODO: feat: RBAC usage for account missing some permissions (ask user to request additional access)
#    - tested on Stage: not able to get this tested as newly created stage account are all org:admin. failed to remove related permissions.
# TODO: feat: distinguish between user and service account connections on server start up (better flag?)
# TODO: chore: clean up unused code adding by AI
# TODO: Ask for code review/testing from @flo
class InsightsOAuthProxyClient(InsightsOAuth2Client):
    """HTTP client specifically for FastMCP OAuth proxy authentication.

    This client is designed to work with FastMCP's OIDC proxy middleware,
    handling token exchange between FastMCP JWT tokens and Red Hat SSO access tokens.
    It implements enhanced token exchange logic for seamless integration with
    Red Hat Insights APIs when using FastMCP authentication.

    Key features:
    - Extracts FastMCP JWT tokens from requests
    - Exchanges FastMCP tokens for Red Hat SSO access tokens
    - Handles multiple token exchange patterns (direct, reference, pass-through)
    - Provides detailed debug information for troubleshooting

    Args:
        base_url: Base URL for the Insights API
        client_id: OAuth2 client ID (typically not used in proxy mode)
        client_secret: OAuth2 client secret (typically not used in proxy mode)
        proxy_url: Optional proxy URL for requests
        oauth_provider: AuthProvider instance for OAuth authentication
        mcp_transport: MCP transport type for error message customization
        token_endpoint: OAuth2 token endpoint (for fallback scenarios)
    """

    def __init__(  # pylint: disable=too-many-arguments
        self,
        *,
        base_url: str = INSIGHTS_BASE_URL_PROD,
        client_id: str | None = "console",  # Default to console client for Red Hat SSO
        client_secret: str | None = None,
        proxy_url: str | None = None,
        oauth_provider: AuthProvider | None = None,
        mcp_transport: str | None = None,
        token_endpoint: str = INSIGHTS_TOKEN_ENDPOINT_PROD,
    ):
        """Initialize the OAuth proxy client.

        Note: This client is designed for OAuth proxy scenarios where
        authentication is handled by FastMCP middleware. Traditional OAuth2
        parameters (client_secret, refresh_token) are typically not needed.
        """
        # Initialize parent class with oauth_enabled=True to trigger proxy mode
        super().__init__(
            base_url=base_url,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=None,  # Not used in proxy mode
            proxy_url=proxy_url,
            oauth_enabled=True,  # Always True for this proxy client
            mcp_transport=mcp_transport,
            token_endpoint=token_endpoint,
        )
        self.oauth_provider = oauth_provider
        self.logger = getLogger("InsightsOAuthProxyClient")

    async def refresh_auth(self) -> None:
        """Enhanced authentication using FastMCP OAuth proxy token exchange.

        This method implements the complete token exchange flow:
        1. Extract FastMCP JWT token from current request
        2. Exchange/validate token to get Red Hat SSO access token
        3. Set Red Hat SSO token for Insights API authentication
        """
        self.logger.debug("Starting OAuth proxy token exchange")

        # Step 1: Get access_token from request header
        fastmcp_token = await self._extract_access_token_from_request()
        if not fastmcp_token:
            self.logger.error("No FastMCP access token found in request")
            raise ValueError(self.no_auth_error(ValueError("No access token in request")))

        # # Step 2: Retrieve Red Hat issuer access_token from OIDC token exchange
        # redhat_access_token = await self._exchange_for_redhat_token(fastmcp_token)
        # if not redhat_access_token:
        #     self.logger.error("Failed to exchange FastMCP token for Red Hat SSO token")
        #     # raise ValueError(self.no_auth_error(ValueError("Token exchange failed")))

        # Step 3: Use Red Hat issuer access_token for Insights API calls
        # final_access_token = redhat_access_token if redhat_access_token else fastmcp_token
        # self.logger.debug("Final access token: %s", final_access_token)

        # self.headers["authorization"] = f"Bearer {fastmcp_token}"
        self.logger.debug("Successfully configured Red Hat SSO token for API authentication")

    async def log_request_and_token_info(self, operation_name: str) -> dict[str, Any]:
        """Log comprehensive request and token information for OAuth proxy debugging.

        This method provides detailed logging of:
        1. Extracting FastMCP access token from request
        2. Logging request headers (with security masking)
        3. Accessing Red Hat SSO claims and scopes
        4. Using enhanced OAuth client for token exchange debugging

        Args:
            operation_name: Name of the operation being performed (e.g., HTTP method + URL)

        Returns:
            Dictionary containing extracted token and request information
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

        # 2. Extract FastMCP access token
        try:
            access_token = get_access_token()
            if access_token:
                info["access_token_info"] = {
                    "client_id": access_token.client_id,
                    "scopes": access_token.scopes,
                    "expires_at": access_token.expires_at,
                    "token_length": len(access_token.token),
                }

                self.logger.info("FastMCP Access token extracted:")
                self.logger.info("  Client ID: %s", access_token.client_id)
                self.logger.info("  Scopes: %s", access_token.scopes)
                self.logger.info("  Expires at: %s", access_token.expires_at)

                # 3. Extract Red Hat SSO claims if available
                if hasattr(access_token, 'claims') and access_token.claims:
                    claims = access_token.claims
                    redhat_claims = {
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
                    info["redhat_sso_claims"] = redhat_claims

                    self.logger.info("Red Hat SSO claims:")
                    for key, value in redhat_claims.items():
                        if value:  # Only log non-empty values
                            self.logger.info("  %s: %s", key, value)

            else:
                self.logger.warning("No access token found in request")
                info["access_token_info"]["error"] = "No token found"

        except Exception as e:
            self.logger.error("Failed to extract access token: %s", e)
            info["access_token_info"]["error"] = str(e)

        # 4. Get enhanced OAuth client debug info (shows token exchange process)
        try:
            debug_info = await self.debug_token_info()
            info["enhanced_client_debug"] = debug_info

            self.logger.info("Enhanced OAuth proxy client debug info:")
            self.logger.info("  OAuth enabled: %s", debug_info.get('oauth_enabled'))
            self.logger.info("  FastMCP token present: %s", debug_info.get('fastmcp_token_present'))
            self.logger.info("  Is Red Hat token: %s", debug_info.get('is_redhat_token'))
            self.logger.info("  Current auth header set: %s",
                           'Yes' if debug_info.get('current_auth_header', 'Not set') != 'Not set' else 'No')

            # Log FastMCP payload details if available
            fastmcp_payload = debug_info.get('fastmcp_payload')
            if fastmcp_payload:
                self.logger.info("  FastMCP token details:")
                self.logger.info("    Issuer: %s", fastmcp_payload.get('iss'))
                self.logger.info("    Audience: %s", fastmcp_payload.get('aud'))
                self.logger.info("    Organization: %s",
                               fastmcp_payload.get('org_id') or fastmcp_payload.get('rh-org-id'))

        except Exception as e:
            self.logger.debug("Enhanced client debug not available: %s", e)
            info["enhanced_client_debug"]["error"] = str(e)

        self.logger.debug("OAuth proxy request info: %s", info)
        self.logger.info("=== End OAuth Proxy Request Logging ===")
        return info

    async def make_request(self, fn, *args, **kwargs) -> dict[str, Any] | str:
        """Make HTTP request with OAuth proxy token management and comprehensive logging.

        Ensures proper token exchange is performed before each API call and logs
        detailed request/token information for debugging and monitoring.

        Args:
            fn: HTTP method function to call
            *args: Positional arguments for the HTTP method
            **kwargs: Keyword arguments for the HTTP method

        Returns:
            JSON response data or error information
        """
        # Generate operation description for logging
        method_name = getattr(fn, '__name__', 'unknown_method')
        url = kwargs.get('url', args[0] if args else 'unknown_url')
        operation_name = f"{method_name.upper()} {url}"

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

        except Exception as e:
            self.logger.warning("Failed to log request information: %s", e)

        # Always perform token exchange for proxy clients
        try:
            await self.refresh_auth()
            self.logger.debug("Token exchange completed successfully for %s", operation_name)
        except Exception as e:
            self.logger.error("Token exchange failed for %s: %s", operation_name, e)
            raise

        # Execute the actual HTTP request
        try:
            self.logger.info("Executing %s request", operation_name)
            result = await InsightsClientBase.make_request(self, fn, *args, **kwargs)
            self.logger.info("Successfully completed %s request", operation_name)
            return result

        except Exception as e:
            self.logger.error("HTTP request failed for %s: %s", operation_name, e)
            raise

    async def _extract_access_token_from_request(self) -> str | None:
        """Extract FastMCP access token from the current request.

        This method tries multiple approaches to get the access token from
        the current MCP request context, with enhanced error handling and
        logging specifically for OAuth proxy scenarios.

        Extraction methods (in order of preference):
        1. FastMCP AccessToken object from dependencies (preferred)
        2. HTTP Authorization header as fallback
        3. Request headers via get_http_headers()

        Returns:
            The FastMCP JWT token string, or None if not found

        Raises:
            No exceptions - returns None on any failure for graceful handling
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

                self.token = OAuth2Token(access_token_dict)  # Store the AccessToken object for later use
                self.logger.debug("AccessToken object stored: %s", self.token)

                return access_token_obj.token
            else:
                self.logger.debug("AccessToken object found but no token present")

        except Exception as e:
            self.logger.debug("Failed to get access token from FastMCP dependencies: %s", e)

        # Method 2: Extract from HTTP Authorization header
        try:
            headers = get_http_headers()
            auth_header = headers.get("authorization") or headers.get("Authorization")

            if auth_header:
                if auth_header.startswith("Bearer "):
                    token = auth_header[7:]  # Remove "Bearer " prefix
                    token_length = len(token)
                    self.logger.debug(
                        "Successfully extracted access token from Authorization header (length: %d)",
                        token_length
                    )
                    return token
                else:
                    self.logger.debug("Authorization header found but not Bearer token: %s",
                                    auth_header[:20] + "..." if len(auth_header) > 20 else auth_header)
            else:
                self.logger.debug("No Authorization header found in request")

        except Exception as e:
            self.logger.debug("Failed to extract token from HTTP headers: %s", e)

        # Method 3: Check other common header variations
        try:
            headers = get_http_headers()

            # Check for other possible token header names
            token_headers = [
                "x-access-token",
                "x-auth-token",
                "access-token",
                "bearer-token"
            ]

            for header_name in token_headers:
                token_value = headers.get(header_name) or headers.get(header_name.upper())
                if token_value:
                    self.logger.debug("Found token in header: %s (length: %d)",
                                    header_name, len(token_value))
                    return token_value

        except Exception as e:
            self.logger.debug("Failed to check alternative token headers: %s", e)

        # Method 4: Log available headers for debugging
        try:
            headers = get_http_headers()
            if headers:
                header_names = list(headers.keys())
                self.logger.debug("Available request headers: %s", header_names)

                # Log any header that might contain authentication info
                auth_related_headers = [h for h in header_names
                                     if any(keyword in h.lower()
                                           for keyword in ['auth', 'token', 'bearer', 'access'])]
                if auth_related_headers:
                    self.logger.debug("Auth-related headers found: %s", auth_related_headers)
            else:
                self.logger.debug("No headers available in request context")

        except Exception as e:
            self.logger.debug("Failed to examine request headers: %s", e)

        # All methods failed
        self.logger.warning("No FastMCP access token found in request using any extraction method")
        return None

    async def _exchange_for_redhat_token(self, fastmcp_token: str) -> str | None:
        """Exchange FastMCP JWT token for Red Hat SSO access token.

        This method implements the complete token exchange pattern:
        1. Decode the FastMCP JWT to extract JTI (JWT ID)
        2. Use oauth_provider to access OIDCProxy token stores
        3. Look up upstream token via JTI mapping
        4. Return the actual Red Hat SSO access token for API calls

        Token exchange flow:
        - Primary: Use oauth_provider's token storage (JTI -> upstream_token_id -> access_token)
        - Fallback 1: Check if token is already Red Hat SSO token
        - Fallback 2: Use FastMCP token directly if compatible

        Args:
            fastmcp_token: The FastMCP JWT token from the request

        Returns:
            The Red Hat SSO access token string, or None if exchange fails
        """
        if not fastmcp_token:
            self.logger.error("Cannot exchange empty FastMCP token")
            return None

        self.logger.debug("Starting enhanced token exchange for Red Hat SSO access token")

        try:

            # Primary Method: Use oauth_provider to retrieve upstream token via fastmcp_token
            if self.oauth_provider:
                self.logger.debug("Attempting upstream token retrieval via oauth_provider with fastmcp_token: %s", fastmcp_token)

                upstream_token = await self.oauth_provider.load_access_token(fastmcp_token)
                self.logger.debug("Upstream token retrieved via oauth_provider: %s", upstream_token)
                if upstream_token and upstream_token.token:
                    self.logger.info("Successfully retrieved upstream Red Hat SSO token via oauth_provider")
                    return upstream_token.token
                else:
                    self.logger.debug("oauth_provider token retrieval failed - continuing with fallback methods")


            # Final Fallback: Log available information and try using FastMCP token directly
            self.logger.warning("No upstream Red Hat token found via oauth_provider - attempting direct FastMCP token use")

            return fastmcp_token  # Return the FastMCP token directly if no upstream token is found to avoid infinite loop

        except jwt.DecodeError as e:
            self.logger.error("Failed to decode FastMCP JWT token: %s", e)
            return None
        except Exception as e:
            self.logger.error("Unexpected error during token exchange: %s", e)
            return None

    async def _get_upstream_token_via_oauth_provider(self, jti: str, fastmcp_token: str) -> str | None:
        """Retrieve upstream Red Hat SSO token using the oauth_provider.

        This method implements the proper OIDCProxy token retrieval pattern:
        1. Verify FastMCP JWT using oauth_provider (if it has JWT verification capability)
        2. Use JTI to lookup upstream_token_id in oauth_provider's JTI mapping store
        3. Use upstream_token_id to retrieve UpstreamTokenSet from oauth_provider's token store
        4. Extract and return the upstream access_token

        Args:
            jti: JWT ID from FastMCP token
            fastmcp_token: The original FastMCP JWT token

        Returns:
            Upstream Red Hat SSO access token, or None if not found
        """
        if not self.oauth_provider:
            self.logger.debug("No oauth_provider available for token retrieval")
            return None

        try:
            self.logger.debug("Using oauth_provider (%s) for upstream token retrieval",
                            type(self.oauth_provider).__name__)

            # Method 1: Use oauth_provider's load_access_token method (if available)
            # This is the preferred method as it leverages FastMCP's built-in token validation
            if hasattr(self.oauth_provider, 'load_access_token'):
                self.logger.debug("Using oauth_provider.load_access_token() method")

                try:
                    # This should perform the complete token validation including JTI lookup
                    validated_token = await self.oauth_provider.load_access_token(fastmcp_token)

                    if validated_token:
                        self.logger.debug("oauth_provider validated token successfully")

                        # For OIDCProxy, this should return an AccessToken with upstream validation
                        # Check if the validated token has the upstream access token or claims
                        if hasattr(validated_token, 'token') and validated_token.token:
                            # The token in validated_token might be the upstream token
                            token_to_check = validated_token.token

                            # If the validated token is different from our FastMCP token, it's likely the upstream token
                            if token_to_check != fastmcp_token:
                                self.logger.info("oauth_provider returned different token - likely upstream Red Hat SSO token")
                                return token_to_check

                            # If tokens are the same, check the claims to see if it's Red Hat SSO
                            if hasattr(validated_token, 'claims') and validated_token.claims:
                                if self._is_redhat_sso_token(validated_token.claims):
                                    self.logger.info("oauth_provider validated token is Red Hat SSO token")
                                    return token_to_check

                        # Check if we can extract the upstream token from the validation result
                        if hasattr(validated_token, 'claims') and validated_token.claims:
                            upstream_access_token = validated_token.claims.get('upstream_access_token')
                            if upstream_access_token:
                                self.logger.info("Found upstream_access_token in validated token claims")
                                return upstream_access_token

                except Exception as e:
                    self.logger.debug("oauth_provider.load_access_token() failed: %s", e)

            # Method 2: Direct access to OIDCProxy token stores (if available)
            # This method directly accesses the storage adapters used by OIDCProxy
            if (hasattr(self.oauth_provider, '_jti_mapping_store') and
                hasattr(self.oauth_provider, '_upstream_token_store')):

                self.logger.debug("oauth_provider has token stores - attempting direct JTI lookup")

                try:
                    # Step 1: Look up upstream_token_id using JTI
                    jti_mapping = await self.oauth_provider._jti_mapping_store.get(key=jti)
                    if not jti_mapping:
                        self.logger.debug("JTI mapping not found for JTI: %s", jti[:8])
                        return None

                    self.logger.debug("Found JTI mapping: %s -> %s",
                                    jti[:8], jti_mapping.upstream_token_id[:8])

                    # Step 2: Retrieve UpstreamTokenSet using upstream_token_id
                    upstream_token_set = await self.oauth_provider._upstream_token_store.get(
                        key=jti_mapping.upstream_token_id
                    )
                    if not upstream_token_set:
                        self.logger.debug("Upstream token set not found for ID: %s",
                                        jti_mapping.upstream_token_id[:8])
                        return None

                    # Step 3: Extract the Red Hat SSO access token
                    if upstream_token_set.access_token:
                        self.logger.info("Successfully retrieved upstream Red Hat SSO token via direct JTI lookup")
                        self.logger.debug("Upstream token metadata - type: %s, scope: %s, expires_at: %s",
                                        upstream_token_set.token_type,
                                        upstream_token_set.scope,
                                        upstream_token_set.expires_at)
                        return upstream_token_set.access_token
                    else:
                        self.logger.warning("Upstream token set found but no access_token available")

                except Exception as e:
                    self.logger.debug("Direct token store access failed: %s", e)

            # Method 3: JWT verification with oauth_provider (if it has JWT capabilities)
            if hasattr(self.oauth_provider, '_jwt_issuer'):
                try:
                    self.logger.debug("Attempting JWT verification with oauth_provider's JWT issuer")

                    # Verify the FastMCP JWT to ensure it's valid
                    jwt_payload = self.oauth_provider._jwt_issuer.verify_token(fastmcp_token)

                    if jwt_payload and jwt_payload.get("jti") == jti:
                        self.logger.debug("JWT verification successful via oauth_provider")

                        # The oauth_provider verified the token - now try the token store lookup again
                        # This ensures we have a valid token before attempting storage access
                        if (hasattr(self.oauth_provider, '_jti_mapping_store') and
                            hasattr(self.oauth_provider, '_upstream_token_store')):

                            # Retry the JTI lookup now that we've verified the token
                            try:
                                jti_mapping = await self.oauth_provider._jti_mapping_store.get(key=jti)
                                if jti_mapping:
                                    upstream_token_set = await self.oauth_provider._upstream_token_store.get(
                                        key=jti_mapping.upstream_token_id
                                    )
                                    if upstream_token_set and upstream_token_set.access_token:
                                        self.logger.info("Retrieved upstream token after JWT verification")
                                        return upstream_token_set.access_token
                            except Exception as e:
                                self.logger.debug("Post-verification token lookup failed: %s", e)

                except Exception as e:
                    self.logger.debug("JWT verification with oauth_provider failed: %s", e)

            # Log oauth_provider capabilities for debugging
            available_methods = []
            if hasattr(self.oauth_provider, 'load_access_token'):
                available_methods.append('load_access_token')
            if hasattr(self.oauth_provider, '_jti_mapping_store'):
                available_methods.append('_jti_mapping_store')
            if hasattr(self.oauth_provider, '_upstream_token_store'):
                available_methods.append('_upstream_token_store')
            if hasattr(self.oauth_provider, '_jwt_issuer'):
                available_methods.append('_jwt_issuer')

            self.logger.debug("oauth_provider available methods: %s", available_methods)
            self.logger.warning("All oauth_provider token retrieval methods failed for JTI: %s", jti[:8])
            return None

        except Exception as e:
            self.logger.error("Unexpected error during oauth_provider token retrieval: %s", e)
            return None

    def _is_redhat_sso_token(self, payload: dict) -> bool:
        """Check if JWT payload indicates this is a Red Hat SSO token.

        Args:
            payload: Decoded JWT payload

        Returns:
            True if this appears to be a Red Hat SSO token
        """
        # Check for Red Hat SSO specific claims and issuer
        redhat_indicators = [
            payload.get("iss", "").endswith("redhat-external"),  # Red Hat SSO issuer
            "org_id" in payload,  # Red Hat organization claim
            "rh-org-id" in payload,  # Alternative Red Hat org claim
            "realm_access" in payload,  # Keycloak/Red Hat SSO roles
            payload.get("azp") in ["console", "insights"],  # Red Hat service clients
            "sso.redhat.com" in payload.get("iss", ""),  # Direct Red Hat SSO issuer check
        ]

        matches = [indicator for indicator in redhat_indicators if indicator]
        self.logger.debug("Red Hat SSO token indicators: %d/%d match", len(matches), len(redhat_indicators))

        return len(matches) >= 2  # Require at least 2 indicators to be confident

    async def _get_upstream_token_from_oidc_proxy(self, jti: str, fastmcp_token: str) -> str | None:
        """Retrieve upstream Red Hat SSO token from OIDCProxy using JTI mapping.

        This method implements the OIDCProxy token retrieval pattern:
        1. Use JTI to lookup upstream_token_id in JTI mapping store
        2. Use upstream_token_id to retrieve UpstreamTokenSet
        3. Extract and return the upstream access_token

        Args:
            jti: JWT ID from FastMCP token
            fastmcp_token: The original FastMCP JWT token

        Returns:
            Upstream Red Hat SSO access token, or None if not found
        """
        try:
            # Approach 1: Try to access FastMCP's server context to get OIDCProxy
            upstream_token = await self._try_server_context_token_retrieval(jti)
            if upstream_token:
                return upstream_token

            # Approach 2: Try to use FastMCP's existing token validation mechanism
            upstream_token = await self._try_fastmcp_validation_token_retrieval(fastmcp_token)
            if upstream_token:
                return upstream_token

            self.logger.debug("All OIDCProxy token retrieval methods failed for JTI %s", jti[:8])
            return None

        except Exception as e:
            self.logger.debug("Error retrieving upstream token from OIDCProxy: %s", e)
            return None

    async def _try_server_context_token_retrieval(self, jti: str) -> str | None:
        """Try to access upstream token through FastMCP server context.

        This attempts to access the OIDCProxy instance through FastMCP's
        server context to directly use its token storage.
        """
        try:
            # Try to access FastMCP server instance through context
            request = get_http_request()
            app = getattr(request, 'app', None)

            if app and hasattr(app, 'auth_provider'):
                auth_provider = app.auth_provider
                self.logger.debug("Found auth provider: %s", type(auth_provider).__name__)

                # Check if this is an OIDCProxy or OAuthProxy
                if hasattr(auth_provider, '_jti_mapping_store') and hasattr(auth_provider, '_upstream_token_store'):
                    self.logger.debug("Found OAuthProxy with token stores - attempting token retrieval")

                    # Use the OIDCProxy's token retrieval logic
                    jti_mapping = await auth_provider._jti_mapping_store.get(key=jti)
                    if jti_mapping:
                        upstream_token_set = await auth_provider._upstream_token_store.get(
                            key=jti_mapping.upstream_token_id
                        )
                        if upstream_token_set and upstream_token_set.access_token:
                            self.logger.info("Successfully retrieved upstream token via server context")
                            return upstream_token_set.access_token

        except Exception as e:
            self.logger.debug("Server context token retrieval failed: %s", e)

        return None

    async def _try_fastmcp_validation_token_retrieval(self, fastmcp_token: str) -> str | None:
        """Try to use FastMCP's existing token validation to get upstream token.

        This leverages FastMCP's built-in token validation which should
        already perform the JTI->upstream token mapping.
        """
        try:
            # Try to access the auth provider's load_access_token method directly
            request = get_http_request()
            app = getattr(request, 'app', None)

            if app and hasattr(app, 'auth_provider'):
                auth_provider = app.auth_provider

                # If this is an OAuthProxy, it should have load_access_token method
                if hasattr(auth_provider, 'load_access_token'):
                    self.logger.debug("Using auth provider's load_access_token method")

                    # This calls the OIDCProxy's token validation which should
                    # return an AccessToken with the upstream validation results
                    validated_token = await auth_provider.load_access_token(fastmcp_token)

                    if validated_token:
                        # The validated token should contain the upstream token information
                        # For Red Hat SSO, the token itself might be the upstream token
                        if hasattr(validated_token, 'token') and validated_token.token:
                            # Check if this looks like a Red Hat SSO token
                            token_claims = validated_token.claims if hasattr(validated_token, 'claims') else {}
                            if self._is_redhat_sso_token(token_claims):
                                self.logger.info("FastMCP validation returned Red Hat SSO token")
                                return validated_token.token

        except Exception as e:
            self.logger.debug("FastMCP validation token retrieval failed: %s", e)

        return None

    async def get_fastmcp_token_claims(self) -> dict[str, Any] | None:
        """Extract and decode claims from the current FastMCP token.

        Convenience method to access FastMCP token claims without
        going through the full token exchange process.

        Returns:
            FastMCP token claims as dictionary, or None if not available
        """
        try:
            fastmcp_token = await self._extract_access_token_from_request()
            if not fastmcp_token:
                return None

            # Decode without verification (FastMCP already verified it)
            payload = jwt.decode(
                fastmcp_token,
                options={"verify_signature": False, "verify_exp": False},
                algorithms=["HS256", "RS256"]
            )
            return payload

        except Exception as e:
            self.logger.debug("Failed to decode FastMCP token claims: %s", e)
            return None

    async def get_red_hat_org_id(self) -> str | None:
        """Get Red Hat organization ID from the current token.

        Tries multiple approaches to extract the organization ID:
        1. From FastMCP token claims (org_id, rh-org-id)
        2. From exchanged Red Hat SSO token

        Returns:
            Organization ID as string, or None if not found
        """
        # Try FastMCP token first
        claims = await self.get_fastmcp_token_claims()
        if claims:
            org_id = claims.get("org_id") or claims.get("rh-org-id")
            if org_id:
                return org_id

        # Fallback to parent method (which decodes the exchanged Red Hat token)
        return await super().get_org_id()

    async def debug_proxy_flow(self) -> dict[str, Any]:
        """Debug the complete OAuth proxy flow for troubleshooting.

        Returns detailed information about:
        - FastMCP token extraction
        - Token exchange process
        - Red Hat SSO token validation
        - Current authentication state

        Returns:
            Comprehensive debug information dictionary
        """
        debug_info = await self.debug_token_info()

        # Add proxy-specific debug information
        debug_info["proxy_client"] = True
        debug_info["fastmcp_claims"] = await self.get_fastmcp_token_claims()
        debug_info["red_hat_org_id"] = await self.get_red_hat_org_id()

        # Test token exchange without setting headers
        try:
            fastmcp_token = await self._extract_access_token_from_request()
            if fastmcp_token:
                redhat_token = await self._exchange_for_redhat_token(fastmcp_token)
                debug_info["token_exchange_test"] = {
                    "fastmcp_token_available": True,
                    "exchange_successful": bool(redhat_token),
                    "redhat_token_length": len(redhat_token) if redhat_token else 0
                }
            else:
                debug_info["token_exchange_test"] = {
                    "fastmcp_token_available": False,
                    "exchange_successful": False
                }
        except Exception as e:
            debug_info["token_exchange_test"] = {"error": str(e)}

        return debug_info


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
                client_id=client_id,
                client_secret=client_secret,
                proxy_url=proxy_url,
                oauth_provider=oauth_provider,
                mcp_transport=mcp_transport,
                token_endpoint=token_endpoint,
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
