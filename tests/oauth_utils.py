"""Utilities for OAuth testing.

This module provides reusable utilities for testing OAuth functionality:
- Mock JWT token creation
- FastMCP AccessToken creation
- Mock SSO server
- OAuth test helpers
"""

import time
from contextlib import contextmanager
from typing import Any
from unittest.mock import Mock, patch

import jwt
from fastmcp.server.auth import AccessToken, AuthProvider


def create_test_jwt(
    claims: dict[str, Any] | None = None,
    expires_in: int = 3600,
    subject: str = "test-user-123",
    issuer: str = "https://sso.redhat.com/auth/realms/redhat-external",
) -> str:
    """Create a test JWT token for OAuth testing.

    Creates a JWT token with realistic Red Hat SSO claims structure
    suitable for testing OAuth flows and token validation.

    Args:
        claims: Custom claims to include or override defaults
        expires_in: Token expiration in seconds (default: 1 hour)
        subject: Token subject (user ID)
        issuer: Token issuer (SSO URL)

    Returns:
        Signed JWT token string

    Example:
        >>> token = create_test_jwt(claims={"organization": {"id": "12345"}})
        >>> decoded = jwt.decode(token, options={"verify_signature": False})
        >>> assert decoded["organization"]["id"] == "12345"
    """
    current_time = int(time.time())

    # Default claims matching Red Hat SSO token structure
    default_claims = {
        "iss": issuer,
        "sub": subject,
        "aud": ["insights-mcp", "api.console"],
        "exp": current_time + expires_in,
        "iat": current_time,
        "auth_time": current_time,
        "jti": f"test-jwt-{current_time}",
        "organization": {
            "id": "test-org-123",
            "name": "Test Organization",
        },
        "account_id": "test-account-456",
        "account_number": "1234567",
        "preferred_username": "test-user",
        "email": "test-user@example.com",
        "email_verified": True,
        "name": "Test User",
        "given_name": "Test",
        "family_name": "User",
        "typ": "Bearer",
        "azp": "insights-mcp",
        "scope": "openid api.console api.ocm",
        "realm_access": {"roles": ["default-roles-redhat-external"]},
        "resource_access": {"insights-mcp": {"roles": ["user"]}},
    }

    # Merge with custom claims
    if claims:
        default_claims.update(claims)

    # Sign with test secret key (HS256 for simplicity in tests)
    token = jwt.encode(default_claims, "test-secret-key-for-oauth-testing", algorithm="HS256")

    return token


def create_test_token(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    org_id: str = "test-org-123",
    user_id: str = "test-user-123",
    username: str = "testuser",
    account_id: str = "test-account-456",
    scopes: list[str] | None = None,
    expires_at: int | None = None,
    email: str = "test@example.com",
    **additional_claims,
) -> AccessToken:
    """Create a test AccessToken for FastMCP OAuth testing.

    Creates a FastMCP AccessToken object with realistic claims structure
    matching Red Hat SSO tokens. This is used to mock the result of
    FastMCP's get_access_token() dependency injection.

    Args:
        org_id: Organization ID for multi-tenant isolation
        user_id: User ID (subject)
        username: Username (preferred_username)
        account_id: Account ID
        scopes: OAuth scopes (default: ["openid", "api.console", "api.ocm"])
        expires_at: Token expiration timestamp (default: 1 hour from now)
        email: User email address
        **additional_claims: Additional JWT claims to include

    Returns:
        FastMCP AccessToken instance ready for testing

    Example:
        >>> token = create_test_token(org_id="org-123", username="alice")
        >>> assert token.claims["organization"]["id"] == "org-123"
        >>> assert token.claims["preferred_username"] == "alice"
    """
    if scopes is None:
        scopes = ["openid", "api.console", "api.ocm"]

    if expires_at is None:
        expires_at = int(time.time()) + 3600  # 1 hour from now

    # Build claims dictionary matching Red Hat SSO structure
    claims = {
        "organization": {"id": org_id, "name": f"Organization {org_id}"},
        "account_id": account_id,
        "account_number": account_id.replace("test-account-", ""),
        "preferred_username": username,
        "email": email,
        "email_verified": True,
        "name": f"Test User {username}",
        "given_name": "Test",
        "family_name": "User",
        **additional_claims,
    }

    # Create JWT token with these claims
    jwt_token = create_test_jwt(claims=claims, expires_in=expires_at - int(time.time()), subject=user_id)

    # Create FastMCP AccessToken
    return AccessToken(
        token=jwt_token, client_id="test-mcp-client", scopes=scopes, expires_at=expires_at, claims=claims
    )


def create_mock_oauth_provider(
    base_url: str = "http://localhost:8000",
    client_id: str = "test-sso-client",
    client_secret: str = "test-sso-secret",
) -> AuthProvider:
    """Create a mock OAuth provider for testing.

    Creates a mock AuthProvider that mimics FastMCP's OIDCProxy
    without requiring real SSO infrastructure.

    Args:
        base_url: Base URL for OAuth callbacks
        client_id: SSO client ID
        client_secret: SSO client secret

    Returns:
        Mock AuthProvider instance

    Example:
        >>> provider = create_mock_oauth_provider()
        >>> assert provider.client_id == "test-sso-client"
    """
    provider = Mock(spec=AuthProvider)
    provider.base_url = base_url
    provider.client_id = client_id
    provider.client_secret = client_secret
    provider.required_scopes = ["openid", "api.console", "api.ocm"]

    # Mock common methods
    provider.authorize = Mock(return_value="/oauth/authorize")
    provider.validate_token = Mock(return_value=True)

    return provider


# OAuth Testing Helpers


def decode_test_token(token: str) -> dict[str, Any]:
    """Decode a test JWT token without signature verification.

    Args:
        token: JWT token string

    Returns:
        Decoded token claims

    Example:
        >>> token = create_test_jwt()
        >>> claims = decode_test_token(token)
        >>> assert "organization" in claims
    """
    return jwt.decode(token, options={"verify_signature": False, "verify_exp": False}, algorithms=["HS256", "RS256"])


def assert_valid_test_token(token: str) -> None:
    """Assert that a token has valid structure for testing.

    Validates:
    - Token can be decoded
    - Has required claims
    - Has organization ID
    - Has expiration

    Args:
        token: JWT token string

    Raises:
        AssertionError: If token is invalid
    """
    claims = decode_test_token(token)

    # Required claims
    assert "iss" in claims, "Token missing issuer"
    assert "sub" in claims, "Token missing subject"
    assert "exp" in claims, "Token missing expiration"
    assert "organization" in claims, "Token missing organization"
    assert "id" in claims["organization"], "Token missing organization ID"


def assert_token_has_claims(token: str, expected_claims: dict[str, Any]) -> None:
    """Assert that a token contains expected claims.

    Args:
        token: JWT token string
        expected_claims: Dictionary of expected claim key-value pairs

    Raises:
        AssertionError: If claims don't match

    Example:
        >>> token = create_test_jwt(claims={"email": "user@test.com"})
        >>> assert_token_has_claims(token, {"email": "user@test.com"})
    """
    claims = decode_test_token(token)

    for key, expected_value in expected_claims.items():
        assert key in claims, f"Token missing claim: {key}"
        assert claims[key] == expected_value, f"Claim {key}: expected {expected_value}, got {claims[key]}"


def extract_org_id_from_token(token: str) -> str | None:
    """Extract organization ID from a JWT token.

    Args:
        token: JWT token string

    Returns:
        Organization ID or None if not found

    Example:
        >>> token = create_test_jwt(claims={"organization": {"id": "org-123"}})
        >>> org_id = extract_org_id_from_token(token)
        >>> assert org_id == "org-123"
    """
    claims = decode_test_token(token)
    return claims.get("organization", {}).get("id")


def create_oauth_test_environment(
    oauth_enabled: bool = True,
    sso_client_id: str = "test-sso-client",
    sso_client_secret: str = "test-sso-secret",
    sso_base_url: str = "http://localhost:9999",
) -> dict[str, Any]:
    """Create environment variables dictionary for OAuth testing.

    Args:
        oauth_enabled: Whether OAuth is enabled
        sso_client_id: SSO client ID
        sso_client_secret: SSO client secret
        sso_base_url: Mock SSO base URL

    Returns:
        Dictionary of environment variables

    Example:
        >>> env = create_oauth_test_environment()
        >>> with patch.dict(os.environ, env):
        ...     # Test OAuth-enabled code
    """
    return {
        "OAUTH_ENABLED": oauth_enabled,
        "SSO_CLIENT_ID": sso_client_id,
        "SSO_CLIENT_SECRET": sso_client_secret,
        "SSO_BASE_URL": sso_base_url,
    }


@contextmanager
def mock_fastmcp_oauth_context(access_token: AccessToken):
    """Mock FastMCP OAuth request context for testing.

    This context manager mocks FastMCP's dependency injection
    to provide an OAuth token in the request context.

    Args:
        access_token: AccessToken to inject into context

    Yields:
        None

    Example:
        >>> token = create_test_token(org_id="org-123")
        >>> with mock_fastmcp_oauth_context(token):
        ...     # Code using get_access_token() will get our token
        ...     from fastmcp.server.dependencies import get_access_token
        ...     retrieved = get_access_token()
        ...     assert retrieved == token
    """
    # Patch both where it's imported and where it's defined
    with patch("insights_mcp.client.get_access_token", return_value=access_token):
        with patch("fastmcp.server.dependencies.get_access_token", return_value=access_token):
            # Also mock headers if needed
            with patch("insights_mcp.client.get_http_headers", return_value={}):
                with patch("fastmcp.server.dependencies.get_http_headers", return_value={}):
                    yield


def create_multi_user_tokens(
    num_users: int = 3,
    base_org_id: str = "org",
) -> dict[str, AccessToken]:
    """Create multiple user tokens for multi-user testing.

    Args:
        num_users: Number of user tokens to create
        base_org_id: Base organization ID (will be suffixed with user number)

    Returns:
        Dictionary mapping user identifiers to AccessTokens

    Example:
        >>> tokens = create_multi_user_tokens(num_users=2)
        >>> assert "user-0" in tokens
        >>> assert "user-1" in tokens
        >>> assert tokens["user-0"].claims["organization"]["id"] != tokens["user-1"].claims["organization"]["id"]
    """
    tokens = {}

    for i in range(num_users):
        user_id = f"user-{i}"
        org_id = f"{base_org_id}-{i:03d}"

        tokens[user_id] = create_test_token(
            org_id=org_id,
            user_id=f"test-{user_id}",
            username=f"testuser{i}",
            account_id=f"account-{i:04d}",
            email=f"user{i}@example.com",
        )

    return tokens


# Token Validation Helpers


def assert_token_has_required_scopes(token: AccessToken, required_scopes: list[str] | None = None) -> None:
    """Assert that a token has required OAuth scopes.

    Args:
        token: AccessToken to check
        required_scopes: List of required scopes (default: ["openid", "api.console", "api.ocm"])

    Raises:
        AssertionError: If token is missing required scopes
    """
    if required_scopes is None:
        required_scopes = ["openid", "api.console", "api.ocm"]

    for scope in required_scopes:
        assert scope in token.scopes, f"Token missing required scope: {scope}"


# Export all public utilities
__all__ = [
    "create_test_jwt",
    "create_test_token",
    "create_mock_oauth_provider",
    "decode_test_token",
    "assert_valid_test_token",
    "assert_token_has_claims",
    "extract_org_id_from_token",
    "create_oauth_test_environment",
    "mock_fastmcp_oauth_context",
    "create_multi_user_tokens",
    "assert_token_has_required_scopes",
]
