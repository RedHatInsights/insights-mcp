"""Unit tests for OAuth client (InsightsOAuthProxyClient).

This module tests the InsightsOAuthProxyClient class which handles
token extraction from FastMCP context and OAuth-authenticated API calls.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from authlib.oauth2.rfc6749 import OAuth2Token

from insights_mcp.client import InsightsOAuthProxyClient
from tests.oauth_utils import (
    create_test_token,
    mock_fastmcp_oauth_context,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def oauth_client():
    """Create a fresh OAuth client instance for each test."""
    return InsightsOAuthProxyClient()


# =============================================================================
# Helper Functions
# =============================================================================


def assert_token_extracted(client, expected_token):
    """Assert that token was successfully extracted."""
    assert client.token is not None
    assert client.token["access_token"] == expected_token.token


def assert_token_metadata(client):
    """Assert that token contains required metadata fields."""
    assert "access_token" in client.token
    assert "scopes" in client.token
    assert "expires_at" in client.token
    assert "client_id" in client.token


def assert_token_has_org_id(token):
    """Assert that token has organization ID in claims."""
    token_claims = token.get("claims")
    assert token_claims is not None, "Token claims are None"
    assert "organization" in token_claims, "Token claims missing 'organization'"
    assert "id" in token_claims["organization"], "Token claims missing 'organization.id'"
    assert token_claims["organization"]["id"], "Organization ID is empty"
    return token_claims["organization"]["id"]


# =============================================================================
# Tests for InsightsOAuthProxyClient
# =============================================================================


class TestInsightsOAuthProxyClientInit:
    """Test OAuth proxy client initialization."""

    def test_client_init_default(self, oauth_client):
        """Test client initialization with default parameters."""
        assert oauth_client.token is None
        assert oauth_client.oauth_provider is None
        assert hasattr(oauth_client, "logger")

    @pytest.mark.parametrize(
        "param,value,attr_name",
        [
            ("base_url", "https://console.stage.redhat.com", "insights_base_url"),
            ("proxy_url", "http://proxy.example.com:8080", "proxy_url"),
        ],
    )
    def test_client_init_with_params(self, param, value, attr_name):
        """Test client initialization with custom parameters."""
        client = InsightsOAuthProxyClient(**{param: value})
        assert getattr(client, attr_name) == value

    def test_client_init_with_oauth_provider(self, mock_oauth_provider):
        """Test client initialization with OAuth provider."""
        client = InsightsOAuthProxyClient(oauth_provider=mock_oauth_provider)
        assert client.oauth_provider == mock_oauth_provider


class TestTokenExtraction:
    """Test token extraction from FastMCP context."""

    @pytest.mark.asyncio
    async def test_token_extraction_success(self, oauth_client, mock_oauth_token):
        """Test successful token extraction from FastMCP context."""
        with mock_fastmcp_oauth_context(mock_oauth_token):
            await oauth_client.refresh_auth()
            assert_token_extracted(oauth_client, mock_oauth_token)
            assert_token_metadata(oauth_client)
            org_id = assert_token_has_org_id(oauth_client.token)
            assert org_id == "test-org-123"

    @pytest.mark.asyncio
    async def test_token_extraction_no_token(self, oauth_client):
        """Test error when no token in request context."""
        with patch("insights_mcp.client.get_access_token", return_value=None):
            with pytest.raises(ValueError, match="No access token"):
                await oauth_client.refresh_auth()

    @pytest.mark.asyncio
    async def test_token_reset_on_refresh(self, oauth_client, mock_oauth_token):
        """Test that token is reset before extraction."""
        oauth_client.token = OAuth2Token({"access_token": "old-token"})

        with mock_fastmcp_oauth_context(mock_oauth_token):
            await oauth_client.refresh_auth()
            assert oauth_client.token["access_token"] == mock_oauth_token.token
            assert oauth_client.token["access_token"] != "old-token"


class TestMakeRequest:
    """Test make_request with OAuth authentication."""

    @pytest.fixture
    def mock_get_response(self):
        """Mock HTTP GET response."""
        response = Mock()
        response.status_code = 200
        response.json.return_value = {"data": "test"}
        return response

    @pytest.mark.asyncio
    async def test_make_request_with_token(self, oauth_client, mock_oauth_token, mock_get_response):
        """Test making request with OAuth token."""
        with mock_fastmcp_oauth_context(mock_oauth_token):
            with patch.object(oauth_client, "get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_get_response

                assert oauth_client.token is None  # before make_request, token should be None
                await oauth_client.make_request(oauth_client.get, url="https://example.com/api/test")
                assert oauth_client.token is not None
                mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_make_request_no_token_error(self, oauth_client):
        """Test make_request fails without token."""
        with patch("insights_mcp.client.get_access_token", return_value=None):
            with pytest.raises(ValueError, match="No access token"):
                await oauth_client.make_request(oauth_client.get, url="https://example.com/api/test")


class TestOrgIdExtraction:
    """Test organization ID extraction from tokens."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "org_id,expected",
        [
            ("test-org-123", "test-org-123"),
            ("custom-org-456", "custom-org-456"),
        ],
    )
    async def test_get_org_id_success(self, oauth_client, org_id, expected):
        """Test successful org ID extraction."""
        token = create_test_token(org_id=org_id) if org_id != "test-org-123" else None

        with mock_fastmcp_oauth_context(token or create_test_token(org_id=org_id)):
            org_id_result = await oauth_client.get_org_id()
            assert org_id_result == expected

    @pytest.mark.asyncio
    async def test_get_org_id_no_token(self, oauth_client):
        """Test error when getting org ID without token."""
        with patch("insights_mcp.client.get_access_token", return_value=None):
            with pytest.raises(ValueError, match="No access token"):
                await oauth_client.get_org_id()

    @pytest.mark.asyncio
    async def test_get_org_id_refreshes_token(self, oauth_client, mock_oauth_token):
        """Test that get_org_id refreshes token from context."""
        assert oauth_client.token is None

        with mock_fastmcp_oauth_context(mock_oauth_token):
            org_id = await oauth_client.get_org_id()
            assert oauth_client.token is not None
            assert org_id == "test-org-123"


class TestTokenScopes:
    """Test token scope handling."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "scopes",
        [
            (["openid", "api.console", "api.ocm"]),
            (["openid", "custom-scope"]),
        ],
    )
    async def test_token_scopes(self, oauth_client, scopes):
        """Test token with different scope configurations."""
        token = create_test_token(scopes=scopes)

        with mock_fastmcp_oauth_context(token):
            await oauth_client.refresh_auth()
            assert set(oauth_client.token["scopes"]) == set(scopes)


class TestTokenClaims:
    """Test token claims extraction and handling."""

    @pytest.mark.asyncio
    async def test_token_claims_accessible(self, oauth_client, mock_oauth_token):
        """Test that token claims are accessible."""
        with mock_fastmcp_oauth_context(mock_oauth_token):
            await oauth_client.refresh_auth()

            claims = oauth_client.token["claims"]
            assert "organization" in claims
            assert "account_id" in claims
            assert "preferred_username" in claims

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "claim_key,claim_value,token_param",
        [
            ("account_id", "account-123", {"account_id": "account-123"}),
            ("preferred_username", "alice", {"username": "alice"}),
        ],
    )
    async def test_claims_extraction(self, oauth_client, claim_key, claim_value, token_param):
        """Test extraction of specific claims from token."""
        token = create_test_token(**token_param)

        with mock_fastmcp_oauth_context(token):
            await oauth_client.refresh_auth()
            assert oauth_client.token["claims"][claim_key] == claim_value


class TestLogging:
    """Test OAuth client logging behavior."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "log_method,raises_error",
        [
            ("debug", False),
            ("error", True),
        ],
    )
    async def test_logs_token_operations(self, oauth_client, mock_oauth_token, log_method, raises_error):
        """Test that token operations are logged."""
        if raises_error:
            with patch("insights_mcp.client.get_access_token", return_value=None):
                with patch.object(oauth_client.logger, log_method) as mock_log:
                    try:
                        await oauth_client.refresh_auth()
                    except ValueError:
                        pass
                    mock_log.assert_called()
        else:
            with mock_fastmcp_oauth_context(mock_oauth_token):
                with patch.object(oauth_client.logger, log_method) as mock_log:
                    await oauth_client.refresh_auth()
                    mock_log.assert_called()

    @pytest.mark.asyncio
    async def test_log_request_and_token_info(self, oauth_client, mock_oauth_token):
        """Test comprehensive logging of request and token info."""
        with mock_fastmcp_oauth_context(mock_oauth_token):
            await oauth_client.refresh_auth()
            info = await oauth_client.log_request_and_token_info("test_operation")
            assert "access_token_info" in info
            assert "request_headers" in info


class TestMultipleRequests:
    """Test behavior across multiple requests."""

    @pytest.mark.asyncio
    async def test_token_isolation_between_requests(self, oauth_client, multi_user_tokens):
        """Test that tokens don't leak between requests."""
        tokens = []
        account_ids = []

        for user_id in ["user-0", "user-1"]:
            with mock_fastmcp_oauth_context(multi_user_tokens[user_id]):
                await oauth_client.refresh_auth()
                tokens.append(oauth_client.token["access_token"])
                account_ids.append(oauth_client.token.get("claims", {}).get("account_id"))

        assert tokens[0] != tokens[1]
        assert account_ids[0] != account_ids[1]
        assert "account-0000" == account_ids[0]
        assert "account-0001" == account_ids[1]


class TestErrorHandling:
    """Test error handling in OAuth client."""

    @pytest.mark.asyncio
    async def test_handles_missing_org_in_token(self, oauth_client):
        """Test handling of token without organization."""
        token = create_test_token()
        token.claims = {"account_id": "test"}

        with mock_fastmcp_oauth_context(token):
            try:
                org_id = await oauth_client.get_org_id()
                assert org_id is None or org_id == ""
            except (KeyError, ValueError, AttributeError):
                pass

    @pytest.mark.asyncio
    async def test_handles_malformed_token(self, oauth_client):
        """Test handling of malformed token."""
        malformed_token = Mock()
        malformed_token.token = "not-a-jwt"
        malformed_token.claims = {}
        malformed_token.model_dump.return_value = {}

        with patch("insights_mcp.client.get_access_token", return_value=malformed_token):
            await oauth_client.refresh_auth()
            assert oauth_client.token is not None


class TestIntegrationScenarios:
    """Integration-style tests for realistic scenarios."""

    @pytest.mark.asyncio
    async def test_concurrent_user_scenario(self, oauth_client, multi_user_tokens):
        """Test scenario with multiple concurrent users."""
        results = []
        for user_id in ["user-0", "user-1", "user-2"]:
            with mock_fastmcp_oauth_context(multi_user_tokens[user_id]):
                await oauth_client.refresh_auth()
                results.append(oauth_client.token["access_token"])

        assert len(set(results)) == 3
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_user_switches_mid_session(self, oauth_client, multi_user_tokens):
        """Test handling when user token changes between calls."""
        results = []
        for user_id in ["user-0", "user-1", "user-0"]:
            with mock_fastmcp_oauth_context(multi_user_tokens[user_id]):
                await oauth_client.refresh_auth()
                results.append(oauth_client.token["access_token"])

        assert results[0] == results[2]  # Same user
        assert results[0] != results[1]  # Different user
