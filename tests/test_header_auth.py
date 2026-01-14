"""Test suite for header-based authentication functionality."""
# pylint: disable=protected-access  # Testing internal authentication methods

from unittest.mock import MagicMock, patch

import pytest

from insights_mcp.client import InsightsHeadersBasedClient, InsightsOAuth2Client
from insights_mcp.server import setup_credentials


class TestHeaderBasedAuthentication:
    """Test suite for header-based authentication functionality."""

    @pytest.mark.asyncio
    async def test_get_credentials_from_headers_sse_transport(self):
        """Test that credentials are extracted from headers for SSE transport."""
        client = InsightsHeadersBasedClient(mcp_transport="sse", token_endpoint="https://test.example.com/token")

        # Mock get_http_headers to return test credentials
        with patch("insights_mcp.client.get_http_headers") as mock_headers:
            mock_headers.return_value = {"insights-client-id": "test-id", "insights-client-secret": "test-secret"}

            client_id, client_secret = client.get_credentials_from_headers()

            assert client_id == "test-id"
            assert client_secret == "test-secret"

    @pytest.mark.asyncio
    async def test_get_credentials_from_headers_http_transport(self):
        """Test that credentials are extracted from headers for HTTP transport."""
        client = InsightsHeadersBasedClient(mcp_transport="http", token_endpoint="https://test.example.com/token")

        # Mock get_http_headers to return test credentials
        with patch("insights_mcp.client.get_http_headers") as mock_headers:
            mock_headers.return_value = {"insights-client-id": "test-id", "insights-client-secret": "test-secret"}

            client_id, client_secret = client.get_credentials_from_headers()

            assert client_id == "test-id"
            assert client_secret == "test-secret"

    @pytest.mark.asyncio
    async def test_get_credentials_from_headers_stdio_transport(self):
        """Test that credentials are NOT extracted from headers for STDIO transport."""
        client = InsightsHeadersBasedClient(mcp_transport="stdio", token_endpoint="https://test.example.com/token")

        # Mock get_http_headers (should not be called)
        with patch("insights_mcp.client.get_http_headers") as mock_headers:
            mock_headers.return_value = {"insights-client-id": "test-id", "insights-client-secret": "test-secret"}

            client_id, client_secret = client.get_credentials_from_headers()

            # Should return None for STDIO transport
            assert client_id is None
            assert client_secret is None

    @pytest.mark.asyncio
    async def test_credentials_priority_env_over_headers(self):
        """Test that environment credentials take priority over headers."""
        client = InsightsOAuth2Client(
            client_id="env-client-id",
            client_secret="env-client-secret",
            mcp_transport="sse",
            token_endpoint="https://test.example.com/token",
        )

        # Mock get_http_headers to return different credentials
        with patch("insights_mcp.client.get_http_headers") as mock_headers:
            mock_headers.return_value = {
                "insights-client-id": "header-client-id",
                "insights-client-secret": "header-client-secret",
            }

            # The instance credentials should be used, not headers
            assert client.client_id == "env-client-id"
            assert client.client_secret == "env-client-secret"

    @pytest.mark.asyncio
    async def test_client_secret_masking_in_logs(self, caplog):
        """Test that client_secret is masked in debug logs."""
        client = InsightsHeadersBasedClient(mcp_transport="sse", token_endpoint="https://test.example.com/token")

        # Mock get_http_headers to return test credentials with long secret
        with patch("insights_mcp.client.get_http_headers") as mock_headers:
            long_secret = "this-is-a-very-long-client-secret-value"
            mock_headers.return_value = {"insights-client-id": "test-id", "insights-client-secret": long_secret}

            with caplog.at_level("DEBUG"):
                client.get_credentials_from_headers()

            # Check that the full secret is NOT in the logs
            assert long_secret not in caplog.text
            # Check that masked version IS in the logs
            assert "this-is-a-" in caplog.text or "***MASKED***" in caplog.text

    @pytest.mark.asyncio
    async def test_no_headers_available(self):
        """Test behavior when no credentials are in headers."""
        client = InsightsHeadersBasedClient(mcp_transport="sse", token_endpoint="https://test.example.com/token")

        # Mock get_http_headers to return empty headers
        with patch("insights_mcp.client.get_http_headers") as mock_headers:
            mock_headers.return_value = {}

            client_id, client_secret = client.get_credentials_from_headers()

            assert client_id is None
            assert client_secret is None

    @pytest.mark.asyncio
    async def test_header_extraction_error_handling(self):
        """Test that header extraction handles errors gracefully."""
        client = InsightsHeadersBasedClient(mcp_transport="sse", token_endpoint="https://test.example.com/token")

        # Mock get_http_headers to raise an exception
        with patch("insights_mcp.client.get_http_headers") as mock_headers:
            mock_headers.side_effect = RuntimeError("No context available")

            client_id, client_secret = client.get_credentials_from_headers()

            # Should return None values instead of raising
            assert client_id is None
            assert client_secret is None


class TestContextSpecificErrorMessages:
    """Test suite for context-specific authentication error messages."""

    @pytest.mark.asyncio
    async def test_error_message_for_env_credentials_sse(self):
        """Test that error message mentions environment credentials when they are set for SSE."""
        client = InsightsOAuth2Client(
            client_id="test-env-id",
            client_secret="test-env-secret",
            mcp_transport="sse",
            token_endpoint="https://test.example.com/token",
        )

        error_msg = client.no_auth_error(ValueError("Invalid credentials"))

        # Should mention environment credentials specifically
        assert "environment credentials" in error_msg.lower()
        assert "LIGHTSPEED_CLIENT_ID" in error_msg or "INSIGHTS_CLIENT_ID" in error_msg
        assert "invalid" in error_msg.lower()
        # Should NOT suggest using headers when env creds are configured
        assert "lightspeed-client-id" not in error_msg.lower() or "which are currently configured" in error_msg

    @pytest.mark.asyncio
    async def test_error_message_for_env_credentials_http(self):
        """Test that error message mentions environment credentials when they are set for HTTP."""
        client = InsightsOAuth2Client(
            client_id="test-env-id",
            client_secret="test-env-secret",
            mcp_transport="http",
            token_endpoint="https://test.example.com/token",
        )

        error_msg = client.no_auth_error(ValueError("Invalid credentials"))

        # Should mention environment credentials specifically
        assert "environment credentials" in error_msg.lower()
        assert "invalid" in error_msg.lower()

    @pytest.mark.asyncio
    async def test_error_message_for_header_credentials_sse(self):
        """Test that error message mentions header credentials when no env vars are set for SSE."""
        client = InsightsOAuth2Client(
            client_id=None, client_secret=None, mcp_transport="sse", token_endpoint="https://test.example.com/token"
        )

        error_msg = client.no_auth_error(ValueError("Missing credentials"))

        # Should mention per-request header credentials specifically
        assert "per-request header" in error_msg.lower() or "header credentials" in error_msg.lower()
        assert "lightspeed-client-id" in error_msg.lower() or "insights-client-id" in error_msg.lower()
        assert "invalid or missing" in error_msg.lower()
        # Should NOT mention environment variables as the primary issue
        assert "environment credentials" not in error_msg.lower()

    @pytest.mark.asyncio
    async def test_error_message_for_header_credentials_http(self):
        """Test that error message mentions header credentials when no env vars are set for HTTP."""
        client = InsightsOAuth2Client(
            client_id=None, client_secret=None, mcp_transport="http", token_endpoint="https://test.example.com/token"
        )

        error_msg = client.no_auth_error(ValueError("Missing credentials"))

        # Should mention header credentials specifically
        assert "header credentials" in error_msg.lower()
        assert "invalid or missing" in error_msg.lower()

    @pytest.mark.asyncio
    async def test_error_message_detects_client_id_only(self):
        """Test that error message detects env creds when only client_id is set."""
        client = InsightsOAuth2Client(
            client_id="test-id",
            client_secret=None,
            mcp_transport="sse",
            token_endpoint="https://test.example.com/token",
        )

        error_msg = client.no_auth_error(ValueError("Invalid credentials"))

        # Should treat this as environment credentials (even with only client_id)
        assert "environment credentials" in error_msg.lower()

    @pytest.mark.asyncio
    async def test_error_message_detects_client_secret_only(self):
        """Test that error message detects env creds when only client_secret is set."""
        client = InsightsOAuth2Client(
            client_id=None,
            client_secret="test-secret",
            mcp_transport="sse",
            token_endpoint="https://test.example.com/token",
        )

        error_msg = client.no_auth_error(ValueError("Invalid credentials"))

        # Should treat this as environment credentials (even with only client_secret)
        assert "environment credentials" in error_msg.lower()

    @pytest.mark.asyncio
    async def test_stdio_error_message_unchanged(self):
        """Test that STDIO transport error messages work correctly."""
        client = InsightsOAuth2Client(
            client_id="test-id",
            client_secret="test-secret",
            mcp_transport="stdio",
            token_endpoint="https://test.example.com/token",
        )

        error_msg = client.no_auth_error(ValueError("Invalid credentials"))

        # STDIO should use the standard message format
        assert "mcp.json config" in error_msg.lower()


class TestProductionWarning:
    """Test suite for production deployment warnings."""

    def test_production_warning_for_http_with_env_credentials(self):
        """Test that warning is emitted for HTTP transport with env credentials."""
        mcp_server_config = {"oauth_enabled": False, "mcp_transport": "http"}
        logger = MagicMock()

        with patch("insights_mcp.server.config") as mock_config:
            mock_config.INSIGHTS_CLIENT_ID = "test-id"
            mock_config.INSIGHTS_CLIENT_SECRET = "test-secret"
            mock_config.INSIGHTS_REFRESH_TOKEN = None
            mock_config.SSO_TOKEN_ENDPOINT = "https://test.example.com/token"

            setup_credentials(mcp_server_config, logger)

            # Check that warning was logged
            warning_calls = [
                call for call in logger.warning.call_args_list if "THIS SHOULD NOT BE USED IN PRODUCTION" in str(call)
            ]
            assert len(warning_calls) > 0

    def test_production_warning_for_sse_with_env_credentials(self):
        """Test that warning is emitted for SSE transport with env credentials."""
        mcp_server_config = {"oauth_enabled": False, "mcp_transport": "sse"}
        logger = MagicMock()

        with patch("insights_mcp.server.config") as mock_config:
            mock_config.INSIGHTS_CLIENT_ID = "test-id"
            mock_config.INSIGHTS_CLIENT_SECRET = "test-secret"
            mock_config.INSIGHTS_REFRESH_TOKEN = None
            mock_config.SSO_TOKEN_ENDPOINT = "https://test.example.com/token"

            setup_credentials(mcp_server_config, logger)

            # Check that warning was logged
            warning_calls = [
                call for call in logger.warning.call_args_list if "THIS SHOULD NOT BE USED IN PRODUCTION" in str(call)
            ]
            assert len(warning_calls) > 0

    def test_no_warning_for_stdio_with_env_credentials(self):
        """Test that NO warning is emitted for STDIO transport with env credentials."""
        mcp_server_config = {"oauth_enabled": False, "mcp_transport": "stdio"}
        logger = MagicMock()

        with patch("insights_mcp.server.config") as mock_config:
            mock_config.INSIGHTS_CLIENT_ID = "test-id"
            mock_config.INSIGHTS_CLIENT_SECRET = "test-secret"
            mock_config.INSIGHTS_REFRESH_TOKEN = None
            mock_config.SSO_TOKEN_ENDPOINT = "https://test.example.com/token"

            setup_credentials(mcp_server_config, logger)

            # Check that warning was NOT logged
            warning_calls = [
                call for call in logger.warning.call_args_list if "THIS SHOULD NOT BE USED IN PRODUCTION" in str(call)
            ]
            assert len(warning_calls) == 0

    def test_no_warning_for_http_with_oauth_enabled(self):
        """Test that NO warning is emitted for HTTP transport with OAuth proxy enabled."""

        mcp_server_config = {"oauth_enabled": True, "mcp_transport": "http"}
        logger = MagicMock()

        with patch("insights_mcp.server.config") as mock_config:
            mock_config.SSO_CLIENT_ID = "test-id"
            mock_config.SSO_CLIENT_SECRET = "test-secret"

            setup_credentials(mcp_server_config, logger)

            # Check that warning was NOT logged (OAuth mode is production-safe)
            warning_calls = [
                call for call in logger.warning.call_args_list if "THIS SHOULD NOT BE USED IN PRODUCTION" in str(call)
            ]
            assert len(warning_calls) == 0
