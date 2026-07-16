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
# TBD split this file into smaller files
# pylint: disable=too-many-lines

import gzip
import json as json_lib
import uuid
from logging import getLogger
from typing import Any

import httpx
import jwt
from authlib.integrations.httpx_client import AsyncOAuth2Client, OAuthError
from authlib.oauth2.rfc6749 import OAuth2Token
from fastmcp.server.dependencies import get_context, get_http_headers

from insights_mcp.config import (
    BRAND_CLIENT_ID_ENV,
    BRAND_CLIENT_ID_HEADER,
    BRAND_CLIENT_SECRET_ENV,
    BRAND_CLIENT_SECRET_HEADER,
    INSIGHTS_BASE_URL,
    INSIGHTS_PROXY_URL,
    SSO_TOKEN_ENDPOINT,
)
from insights_mcp.errors import InsightsApiError
from insights_mcp.session_cache import SessionCache

from . import __version__

USER_AGENT = f"insights-mcp/{__version__}"

# SSO claim keys containing PII (personally identifiable information); masked in logs for ISO 27018 compliance
_PII_CLAIM_KEYS = frozenset({"subject", "account_id", "username", "email"})


def _extract_bearer_token_from_auth_header(auth_header: str) -> str:
    if auth_header and auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()
    return ""


def _get_authorization_bearer_token(mcp_transport: str | None) -> str:
    """Return bearer token from the Authorization header, or empty string."""
    if mcp_transport not in ("sse", "http"):
        return ""
    try:
        headers = get_http_headers(include={"authorization"})
        auth_header = headers.get("authorization") or headers.get("Authorization") or ""
        return _extract_bearer_token_from_auth_header(auth_header)
    except (RuntimeError, KeyError, AttributeError):
        return ""


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
        # Will be set by subclasses to indicate if using environment credentials
        self._using_env_credentials = False
        # Will be set by subclasses to indicate the auth method used for this request
        self._request_auth_method: str | None = None

    async def make_request(self, fn, *args, **kwargs) -> dict[str, Any] | str:
        """Make an HTTP request with error handling.

        Args:
            fn: HTTP method function to call (e.g., self.get, self.post)
            *args: Positional arguments for the HTTP method
            **kwargs: Keyword arguments for the HTTP method

        Returns:
            JSON response data or plain-text body on success

        Raises:
            InsightsApiError: If the HTTP request fails or an unhandled error occurs
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
            raise InsightsApiError(self.get_error_message(e)) from e
        except Exception as exc:
            raise InsightsApiError(str(exc)) from exc

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
        """Generate authentication error message based on transport type and credential source.

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
        )
        error_message = str(e)
        # strip off "401 Unauthorized"
        # this confuses LLMs
        # just replacing with a nice text which can be found in logs later :-D
        error_message = error_message.replace("401 Unauthorized", "THE request problem")
        error_message = error_message.replace(
            "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/401", "relevant MCP functions"
        )

        # Construct the return message based on the transport type and auth method used for this request
        return_message = f"{base_message}"

        # For HTTP/SSE transports with NO instance credentials, use header auth message
        if self.mcp_transport in ["sse", "http"] and not self._using_env_credentials:
            if self._request_auth_method == "header_based_bearer_token_auth":
                return_message += (
                    "The user should ensure the JWT token in the `Authorization: Bearer <token>` "
                    "header is valid and not expired first. If it is expired or invalid, the user should "
                    "refresh or replace the token in the MCP client configuration and try the request again.\n "
                    f"OR consider using the header credentials `{BRAND_CLIENT_ID_HEADER}` and "
                    f"`{BRAND_CLIENT_SECRET_HEADER}` to authenticate the request. If this is the case, "
                )

            return_message += (
                f"The user should go to [{self.insights_base_url}]({self.insights_base_url}) to "
                "Click Settings (⚙️ Gear Icon) ➡ Service Accounts ➡ create a service account and then set the "
                f"header credentials `{BRAND_CLIENT_ID_HEADER}` and `{BRAND_CLIENT_SECRET_HEADER}` "
                "in your request (they are invalid or missing).\n"
            )

        # For STDIO or when using environment credentials, use environment auth message
        else:
            return_message += (
                f"The user should go to [{self.insights_base_url}]({self.insights_base_url}) to "
                "Click Settings (⚙️ Gear Icon) ➡ Service Accounts ➡ create a service account and then set the "
                f"environment credentials `{BRAND_CLIENT_ID_ENV}` and `{BRAND_CLIENT_SECRET_ENV}` "
                "in your mcp.json config (they are invalid or missing).\n"
            )

        # Concate the shared tail message
        return_message += (
            "Here is the direct link for the user's convenience: "
            f"[{self.insights_base_url}/iam/service-accounts]({self.insights_base_url}/iam/service-accounts) "
            "Come up with a detailed description of this for the user. "
            "Only describe this, don't expose details about the tool function itself. "
            f"Don't proceed with the request before this is fixed. {error_message}"
        )

        return return_message

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
        base_url: str = INSIGHTS_BASE_URL,
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


class InsightsBearerTokenClient(InsightsClientBase):
    """HTTP client that uses a pre-existing Bearer token for Red Hat Insights APIs.

    This client uses a JWT Bearer token directly, without any OAuth2 token exchange.
    The token is set as-is in the Authorization header for all API requests.

    This is used when callers provide an Authorization: Bearer <token> header in
    SSE/HTTP transports, allowing authentication with a pre-existing JWT token
    instead of service account credentials.

    Args:
        bearer_token: The JWT Bearer token to use for authentication
        base_url: Base URL for the Insights API
        proxy_url: Optional proxy URL for requests
        mcp_transport: MCP transport type for error message customization
    """

    def __init__(
        self,
        *,
        bearer_token: str,
        base_url: str = INSIGHTS_BASE_URL,
        proxy_url: str | None = None,
        mcp_transport: str | None = None,
    ):
        super().__init__(base_url=base_url, proxy_url=proxy_url, mcp_transport=mcp_transport)
        self._bearer_token = bearer_token
        self.headers["authorization"] = f"Bearer {bearer_token}"
        self.logger = getLogger("InsightsBearerTokenClient")
        self._using_env_credentials = False
        self._request_auth_method = "header_based_bearer_token_auth"

    async def make_request(self, fn, *args, **kwargs) -> dict[str, Any] | str:
        """Make an HTTP request with the pre-set Bearer token.

        No token refresh or exchange is needed -- the token is used as-is.

        Args:
            fn: HTTP method function to call (e.g., self.get, self.post)
            *args: Positional arguments for the HTTP method
            **kwargs: Keyword arguments for the HTTP method

        Returns:
            JSON response data or error information
        """
        return await super().make_request(fn, *args, **kwargs)

    async def get_org_id(self) -> str | None:
        """Extract the organization ID from the Bearer JWT token.

        Decodes the JWT without verification to extract the rh-org-id claim.

        Returns:
            Organization ID (rh-org-id) as a string, or None if not found.
        """
        try:
            decoded = jwt.decode(
                self._bearer_token,
                options={"verify_signature": False},
                algorithms=["RS256"],
            )
            return decoded.get("rh-org-id")
        except jwt.DecodeError:
            self.logger.debug("Failed to decode bearer token JWT for org_id extraction")
            return None

    async def get_user_id(self) -> str | None:
        """Extract the user ID from the Bearer JWT token.

        Returns:
            User ID (rh-user-id) as a string, or None if not found.
        """
        try:
            decoded = jwt.decode(
                self._bearer_token,
                options={"verify_signature": False},
                algorithms=["RS256"],
            )
            return decoded.get("rh-user-id")
        except jwt.DecodeError:
            self.logger.debug("Failed to decode bearer token JWT for user_id extraction")
            return None


class InsightsOAuth2Client(InsightsClientBase, AsyncOAuth2Client):
    """HTTP client with traditional OAuth2 authentication for Red Hat Insights APIs.

    This client handles traditional OAuth2 flows without FastMCP proxy integration:
    1. Service account (client credentials) flow - uses client_id + client_secret
    2. Refresh token flow - uses refresh_token for long-lived sessions


    Args:
        base_url: Base URL for the Insights API
        client_id: OAuth2 client ID
        client_secret: OAuth2 client secret for service account authentication
        refresh_token: OAuth2 refresh token for user authentication
        proxy_url: Optional proxy URL for requests
        mcp_transport: MCP transport type for error message customization
        token_endpoint: OAuth2 token endpoint URL
    """

    def __init__(  # pylint: disable=too-many-arguments
        self,
        *,
        base_url: str = INSIGHTS_BASE_URL,
        client_id: str | None = "rhsm-api",
        client_secret: str | None = None,
        refresh_token: str | None = None,
        proxy_url: str | None = None,
        mcp_transport: str | None = None,
        token_endpoint: str = SSO_TOKEN_ENDPOINT,
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
        # Cache whether we're using environment credentials (set once at init)
        self._using_env_credentials = bool(client_id or client_secret)
        self._request_auth_method = "oauth2_client_credentials_auth"

        # Verify proxy configuration after initialization
        if proxy_url:
            self.logger.debug("InsightsOAuth2Client initialized with proxy: %s", proxy_url)
            if hasattr(self, "_transport") and hasattr(self._transport, "_pool"):
                self.logger.debug("Proxy verification: httpx transport configured")
            elif hasattr(self, "_mounts"):
                self.logger.debug("Proxy verification: httpx mounts configured")
        else:
            self.logger.debug("InsightsOAuth2Client initialized without proxy")

    async def refresh_auth(self) -> None:
        """Refresh the authentication token."""
        self.logger.debug("Starting token refresh")
        if "access_token" not in self.token or self.token.is_expired():
            self.logger.debug("Token is expired, refreshing token")
            try:
                if "refresh_token" in self.token:
                    await self.refresh_token()
                else:
                    await self.fetch_token()
            except OAuthError as e:
                raise ValueError(self.no_auth_error(e)) from e
        else:
            self.logger.debug("Token is valid, skipping token refresh")

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
        if self.refresh_token is None and self.client_secret is None:
            raise InsightsApiError(self.no_auth_error(ValueError("Client not authenticated")))

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


class InsightsHeadersBasedClient:  # pylint: disable=too-many-instance-attributes
    """Client factory for multiuser scenarios with per-connection header credentials and session caching.

    This is a factory class (uses composition, not inheritance) that creates isolated
    InsightsOAuth2Client instances for each request. It's designed for SSE/HTTP transports
    where multiple users make requests to the same server instance, each providing their
    own credentials via HTTP headers.

    Key behaviors:
    - Extracts client_id and client_secret from HTTP headers on each request
    - Uses FastMCP's session_id for per-connection token caching
    - Caches tokens with TTL (default 5 minutes) to reduce Red Hat SSO load
    - Creates isolated client instances per request for complete thread-safety
    - Maintains isolation: different connections or credentials = separate cache entries
    - Raises authentication errors immediately if header credentials are missing

    This ensures proper security isolation between different users' requests while
    providing optimal performance through intelligent caching.

    Args:
        base_url: Base URL for the Insights API
        proxy_url: Optional proxy URL for requests
        mcp_transport: MCP transport type for error message customization
        token_endpoint: OAuth2 token endpoint URL
    """

    # Class-level cache shared across all instances for efficient multiuser support
    # Uses FastMCP session_id for connection-level isolation as recommended by FastMCP docs
    _session_cache = None  # Lazy initialization

    def __init__(
        self,
        *,
        base_url: str = INSIGHTS_BASE_URL,
        proxy_url: str | None = None,
        mcp_transport: str | None = None,
        token_endpoint: str = SSO_TOKEN_ENDPOINT,
    ):
        """Initialize the headers-based client factory with session caching.

        Note: This client uses FastMCP's session_id for per-connection token caching,
        providing optimal performance while maintaining security isolation between
        different client connections and credentials.
        """
        # Store configuration for creating clients
        self.insights_base_url = base_url
        self.proxy_url = proxy_url
        self.mcp_transport = mcp_transport
        self.token_endpoint = token_endpoint
        self._using_env_credentials = False
        self._request_auth_method = "header_based_client_credentials_auth"

        self.logger = getLogger("InsightsHeadersBasedClient")

        # Initialize helper client for utility methods (NOT for API requests)
        self._helper = InsightsOAuth2Client(
            base_url=base_url,
            client_id=None,
            client_secret=None,
            refresh_token=None,
            proxy_url=proxy_url,
            mcp_transport=mcp_transport,
            token_endpoint=token_endpoint,
        )

    def get_credentials_from_headers(self) -> tuple[str | None, str | None]:
        """Extract client credentials from HTTP headers for SSE/HTTP transports.

        This method is used to support per-request authentication in multi-user scenarios
        where credentials are provided via HTTP headers rather than environment variables.

        Returns:
            Tuple of (client_id, client_secret) or (None, None) if not available

        Note:
            - STDIO transport always returns (None, None) as it doesn't support headers
            - SSE/HTTP transports extract from insights-client-id/insights-client-secret headers
            - Also checks lightspeed-client-id/lightspeed-client-secret as brand aliases
            - Client secrets are masked in debug logs for security
        """
        # STDIO transport doesn't support header-based credentials
        if self.mcp_transport == "stdio":
            return None, None

        # Only extract credentials for SSE/HTTP transports
        if self.mcp_transport not in ["sse", "http"]:
            return None, None

        try:
            headers = get_http_headers()
            # Try lightspeed brand headers first
            client_id = headers.get("lightspeed-client-id")
            client_secret = headers.get("lightspeed-client-secret")

            # Fall back to insights brand headers
            if not client_id:
                client_id = headers.get("insights-client-id")
            if not client_secret:
                client_secret = headers.get("insights-client-secret")

            if client_id or client_secret:
                # Mask the secret in logs for security
                if client_secret:
                    masked_secret = "client_secret=***MASKED***"
                else:
                    masked_secret = "(no secret provided)"

                self.logger.debug("Extracted credentials from headers: client_id=%s, %s", client_id, masked_secret)

            return client_id, client_secret

        except (RuntimeError, KeyError, AttributeError) as e:
            # Headers not available (e.g., not in request context)
            self.logger.debug("Failed to extract credentials from headers: %s", e)
            return None, None

    def get_bearer_token_from_headers(self) -> str | None:
        """Extract Bearer token from the Authorization HTTP header.

        This method checks for an Authorization: Bearer <token> header in the
        current HTTP request, used for SSE/HTTP transports where callers provide
        a pre-existing JWT token instead of service account credentials.

        Returns:
            The bearer token string (without prefix) if found, None otherwise.

        Note:
            - STDIO transport always returns None as it doesn't support headers
            - Only SSE/HTTP transports are checked
            - The "Bearer " prefix is case-insensitive
        """
        bearer_token = _get_authorization_bearer_token(self.mcp_transport)
        self.logger.debug(
            "Bearer token from Authorization header: %s",
            f"present ({len(bearer_token)} chars)" if bearer_token else "absent",
        )
        return bearer_token or None

    async def _get_authenticated_client(
        self, session_id: str, client_id: str, client_secret: str
    ) -> InsightsOAuth2Client:
        """Get or create authenticated client with cached token.

        This method combines token fetching and client creation into a single operation,
        avoiding double instantiation. It checks the cache first, fetches a new token
        if needed, then creates a client with the valid token.

        Args:
            session_id: FastMCP session ID for this connection
            client_id: OAuth client ID from request headers
            client_secret: OAuth client secret from request headers

        Returns:
            InsightsOAuth2Client with valid token, ready for API requests

        Raises:
            ValueError: If token fetch fails
        """
        # Ensure session cache is initialized
        if self._session_cache is None:
            InsightsHeadersBasedClient._session_cache = SessionCache()

        # Cache is guaranteed to be initialized at this point
        assert self._session_cache is not None  # for mypy

        # Try cache first (keyed by session_id + credentials)
        cached_token = self._session_cache.get(session_id, client_id, client_secret)

        if not cached_token or cached_token.is_expired():
            # Cache miss or expired - create client, fetch token, cache it, and return the same client
            self.logger.debug(
                "Fetching new OAuth token for session %s", session_id[:8] if len(session_id) >= 8 else session_id
            )

            client = InsightsOAuth2Client(
                base_url=self.insights_base_url,
                client_id=client_id,
                client_secret=client_secret,
                proxy_url=self.proxy_url,
                mcp_transport=self.mcp_transport,
                token_endpoint=self.token_endpoint,
            )

            try:
                await client.fetch_token()
                # Cache the new token for this session
                self._session_cache.set(
                    session_id, client_id=client_id, client_secret=client_secret, token=client.token
                )
                self.logger.debug(
                    "Successfully cached new token for session %s",
                    session_id[:8] if len(session_id) >= 8 else session_id,
                )
                return client  # Return without closing - caller will close it
            except OAuthError as e:
                await client.aclose()  # Only close on error
                self.logger.error(
                    "OAuth token fetch failed for session %s: %s",
                    session_id[:8] if len(session_id) >= 8 else session_id,
                    e,
                )
                raise ValueError(self._helper.no_auth_error(e)) from e
        else:
            # Cache hit - create new client with cached token
            self.logger.debug(
                "Using cached token for session %s", session_id[:8] if len(session_id) >= 8 else session_id
            )

            client = InsightsOAuth2Client(
                base_url=self.insights_base_url,
                client_id=client_id,
                client_secret=client_secret,
                proxy_url=self.proxy_url,
                mcp_transport=self.mcp_transport,
                token_endpoint=self.token_endpoint,
            )
            client.token = cached_token
            return client

    async def refresh_auth(self) -> None:
        """Extract credentials from headers and ensure valid token in cache.

        This method is maintained for compatibility with parent class API.
        It extracts credentials and ensures a valid token exists, setting self.token.

        Checks for Bearer token first, then falls back to client_id/secret headers.

        Note: For actual request execution, use make_request() which creates
        isolated per-request clients for thread-safety.

        Raises:
            ValueError: If no credentials are found in request headers or token fetch fails
        """
        self.logger.debug("Starting header-based auth with FastMCP session caching")

        # Check for Bearer token first
        bearer_token = self.get_bearer_token_from_headers()
        if bearer_token:
            self.logger.debug("Bearer token found in headers, no refresh needed")
            self.token = {"access_token": bearer_token}  # pylint: disable=attribute-defined-outside-init
            return

        # Extract credentials from current request headers
        client_id, client_secret = self.get_credentials_from_headers()

        if not client_id or not client_secret:
            error_msg = (
                "No credentials found in request headers. "
                f"Expected `Authorization: Bearer <token>` header, or "
                f"`{BRAND_CLIENT_ID_HEADER}` and `{BRAND_CLIENT_SECRET_HEADER}` headers."
            )
            self.logger.debug(error_msg)
            raise ValueError(self._helper.no_auth_error(ValueError(error_msg)))

        # Get FastMCP session_id for connection-level caching
        session_id = self._get_session_id()

        # Get authenticated client (fetches token if needed, creates client with cached token)
        temp_client = await self._get_authenticated_client(session_id, client_id, client_secret)
        try:
            self.token = temp_client.token  # pylint: disable=attribute-defined-outside-init
        finally:
            await temp_client.aclose()

    async def make_request(self, method_name_or_fn, *args, **kwargs) -> dict[str, Any] | str:
        """Execute HTTP request with per-request isolated client for thread-safety.

        This method first checks for a Bearer token in the Authorization header. If found,
        it creates an InsightsBearerTokenClient that uses the token directly. Otherwise,
        it falls back to extracting client_id/secret from headers and creating an
        InsightsOAuth2Client instance with cached token exchange.

        Args:
            method_name_or_fn: HTTP method name string ('get', 'post', etc.) or method name from __getattr__
            *args: Positional arguments for the HTTP method
            **kwargs: Keyword arguments for the HTTP method

        Returns:
            JSON response data as dict, plain text as str, or error information

        Raises:
            ValueError: If credentials are missing or authentication fails
            httpx.HTTPStatusError: If the API request fails with HTTP error

        Note:
            Each request uses an isolated client instance, preventing race conditions
            when multiple users make concurrent requests with different credentials.
        """
        # Check for Bearer token first (highest priority for header-based auth)
        bearer_token = self.get_bearer_token_from_headers()
        if bearer_token:
            bearer_client = InsightsBearerTokenClient(
                bearer_token=bearer_token,
                base_url=self.insights_base_url,
                proxy_url=self.proxy_url,
                mcp_transport=self.mcp_transport,
            )
            try:
                if isinstance(method_name_or_fn, str):
                    method = getattr(bearer_client, method_name_or_fn)
                else:
                    method = getattr(bearer_client, method_name_or_fn)
                return await bearer_client.make_request(method, *args, **kwargs)
            finally:
                await bearer_client.aclose()

        # Fall back to client_id/secret from headers
        client_id, client_secret = self.get_credentials_from_headers()

        if not client_id or not client_secret:
            error_msg = (
                "No credentials found in request headers. "
                f"Expected `Authorization: Bearer <token>` header, or "
                f"`{BRAND_CLIENT_ID_HEADER}` and `{BRAND_CLIENT_SECRET_HEADER}` headers."
            )
            self.logger.debug(error_msg)
            raise ValueError(self._helper.no_auth_error(ValueError(error_msg)))

        # Get FastMCP session_id for connection-level caching
        session_id = self._get_session_id()

        # Get authenticated client (fetches token if needed, returns ready-to-use client)
        request_client = await self._get_authenticated_client(session_id, client_id, client_secret)

        try:
            # Handle both string method names (from __getattr__) and direct calls
            if isinstance(method_name_or_fn, str):
                method = getattr(request_client, method_name_or_fn)
            else:
                # method_name_or_fn is actually a string from __getattr__, treat as method name
                method = getattr(request_client, method_name_or_fn)
            return await request_client.make_request(method, *args, **kwargs)
        finally:
            # Always clean up the request client to avoid connection leaks
            await request_client.aclose()

    def _get_session_id(self) -> str:
        """Get FastMCP session ID for connection-level caching.

        Retrieves the session_id from FastMCP's Context, which is persistent across
        multiple requests from the same client connection. This is the FastMCP-recommended
        approach for "session-based data storage" as documented in FastMCP's server context.

        Returns:
            Session ID from FastMCP context, or fallback ID for stdio/unknown transports

        Note:
            For HTTP/SSE transports, this returns the MCP session ID that remains constant
            across multiple requests from the same client. For STDIO transport, it returns
            a single session identifier since STDIO typically represents a single connection.
        """
        try:
            ctx = get_context()
            if ctx and ctx.session_id:
                return ctx.session_id
        except (RuntimeError, AttributeError) as e:
            self.logger.debug("Unable to get FastMCP session_id: %s", e)

        # Fallback for stdio or when context unavailable
        if self.mcp_transport == "stdio":
            return "stdio-single-session"

        # For HTTP/SSE without context, generate from connection info
        # This is a fallback and shouldn't normally happen in proper FastMCP setup
        fallback_id = f"fallback-{uuid.uuid4().hex[:16]}"
        self.logger.warning("Using fallback session ID (FastMCP context unavailable): %s", fallback_id[:16])
        return fallback_id

    def __getattr__(self, name: str):
        """Delegate attribute access to create per-request clients.

        This magic method makes InsightsHeadersBasedClient compatible with code that accesses
        `client.get`, `client.post`, etc. as attributes (for use with make_request).

        When code does `client.make_request(client.get, ...)`, this returns a callable
        that will be used by make_request().

        Args:
            name: Attribute name being accessed

        Returns:
            Callable for HTTP methods that can be used with make_request()

        Raises:
            AttributeError: If the attribute is not an HTTP method
        """
        # Only delegate HTTP methods
        if name in ("get", "post", "put", "delete", "patch"):
            # Return a simple marker that make_request() can recognize
            # The actual method will be retrieved from the temporary client
            return name

        # For other attributes, raise AttributeError
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    async def get_org_id(self) -> str | None:
        """Extract organization ID using temporary client.

        Checks for Bearer token first, then falls back to client_id/secret headers.

        Returns:
            Organization ID (rh-org-id) as a string, or None if not found.

        Raises:
            ValueError: If credentials are missing or authentication fails
        """
        # Check for Bearer token first
        bearer_token = self.get_bearer_token_from_headers()
        if bearer_token:
            bearer_client = InsightsBearerTokenClient(
                bearer_token=bearer_token,
                base_url=self.insights_base_url,
                proxy_url=self.proxy_url,
                mcp_transport=self.mcp_transport,
            )
            try:
                return await bearer_client.get_org_id()
            finally:
                await bearer_client.aclose()

        # Fall back to client_id/secret from headers
        client_id, client_secret = self.get_credentials_from_headers()

        if not client_id or not client_secret:
            error_msg = (
                "No credentials found in request headers. "
                f"Expected `Authorization: Bearer <token>` header, or "
                f"`{BRAND_CLIENT_ID_HEADER}` and `{BRAND_CLIENT_SECRET_HEADER}` headers."
            )
            self.logger.debug(error_msg)
            raise ValueError(self._helper.no_auth_error(ValueError(error_msg)))

        # Get FastMCP session_id for connection-level caching
        session_id = self._get_session_id()

        # Get authenticated client (fetches token if needed, returns ready-to-use client)
        request_client = await self._get_authenticated_client(session_id, client_id, client_secret)

        try:
            return await request_client.get_org_id()
        finally:
            await request_client.aclose()


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
        mcp_transport: MCP transport type for error message customization
    """

    # mypy type annotation: client is always initialized, never None
    client: InsightsOAuth2Client | InsightsHeadersBasedClient

    def __init__(  # pylint: disable=too-many-arguments
        self,
        *,
        api_path: str,
        base_url: str = INSIGHTS_BASE_URL,
        client_id: str | None = "rhsm-api",
        client_secret: str | None = None,
        refresh_token: str | None = None,
        headers: dict[str, str] | None = None,
        proxy_url: str | None = INSIGHTS_PROXY_URL,
        mcp_transport: str | None = None,  # TODO: get rid of mcp_transport in client
        token_endpoint: str = SSO_TOKEN_ENDPOINT,
    ):
        self.logger = getLogger("InsightsClient")

        # TBD: hand over toolset_name for better logging
        self.logger.info("Initializing insights client for %s", api_path)

        self.insights_base_url = base_url
        self.api_path = api_path
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.headers = headers
        self.proxy_url = proxy_url
        self.mcp_transport = mcp_transport
        self.token_endpoint = token_endpoint

        self.client_noauth = InsightsNoauthClient(base_url=base_url, proxy_url=proxy_url, mcp_transport=mcp_transport)

        if refresh_token or client_secret:
            # Use traditional OAuth2 client for service account/refresh token flows
            self.client = InsightsOAuth2Client(
                base_url=base_url,
                client_id=client_id,
                client_secret=client_secret,
                refresh_token=refresh_token,
                proxy_url=proxy_url,
                mcp_transport=mcp_transport,
                token_endpoint=token_endpoint,
            )
        else:
            self.client = InsightsHeadersBasedClient(
                base_url=base_url,
                proxy_url=proxy_url,
                mcp_transport=mcp_transport,
                token_endpoint=token_endpoint,
            )

        # merge headers with client headers
        if headers:
            self.logger.info("Updating client headers with %s", headers)
            if hasattr(self.client, "headers"):
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
            JSON response data or plain-text body on success

        Raises:
            InsightsApiError: If authentication fails or the API request fails
        """
        try:
            client = self.client_noauth if noauth else self.client
            url = f"{self.insights_base_url}/{self.api_path}/{endpoint}"
            return await client.make_request(client.get, url=url, params=params, **kwargs)
        except ValueError as e:
            raise InsightsApiError(str(e)) from e

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
            JSON response data or plain-text body on success

        Raises:
            InsightsApiError: If authentication fails or the API request fails
        """
        try:
            client = self.client_noauth if noauth else self.client
            url = f"{self.insights_base_url}/{self.api_path}/{endpoint}"
            return await client.make_request(client.post, url=url, json=json, **kwargs)
        except ValueError as e:
            raise InsightsApiError(str(e)) from e

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
            JSON response data or plain-text body on success

        Raises:
            InsightsApiError: If authentication fails or the API request fails
        """
        try:
            client = self.client_noauth if noauth else self.client
            url = f"{self.insights_base_url}/{self.api_path}/{endpoint}"
            return await client.make_request(client.put, url=url, json=json, **kwargs)
        except ValueError as e:
            raise InsightsApiError(str(e)) from e
