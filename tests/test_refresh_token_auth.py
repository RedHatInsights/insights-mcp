"""Tests for refresh-token authentication credential handling."""

from unittest.mock import MagicMock, patch

from insights_mcp.client import InsightsClient, InsightsOAuth2Client
from insights_mcp.server import setup_credentials


class TestRefreshTokenAuth:
    """Test credential normalization and client defaults for refresh-token authentication."""

    def test_setup_credentials_coerces_empty_client_id_when_refresh_token_set(self):
        """Empty INSIGHTS_CLIENT_ID should become None so rhsm-api default applies."""
        mcp_server_config = {"oauth_enabled": False, "mcp_transport": "stdio"}
        logger = MagicMock()

        with patch("insights_mcp.server.config") as mock_config:
            mock_config.INSIGHTS_CLIENT_ID = ""
            mock_config.INSIGHTS_CLIENT_SECRET = ""
            mock_config.INSIGHTS_REFRESH_TOKEN = "test-refresh-token"
            mock_config.SSO_TOKEN_ENDPOINT = "https://test.example.com/token"

            setup_credentials(mcp_server_config, logger)

        assert mcp_server_config["client_id"] is None
        assert mcp_server_config["client_secret"] is None
        assert mcp_server_config["refresh_token"] == "test-refresh-token"
        logger.error.assert_not_called()

    def test_setup_credentials_refresh_token_only_does_not_log_missing_credentials(self):
        """Refresh token alone is sufficient for STDIO credential setup."""
        mcp_server_config = {"oauth_enabled": False, "mcp_transport": "stdio"}
        logger = MagicMock()

        with patch("insights_mcp.server.config") as mock_config:
            mock_config.INSIGHTS_CLIENT_ID = ""
            mock_config.INSIGHTS_CLIENT_SECRET = ""
            mock_config.INSIGHTS_REFRESH_TOKEN = "test-refresh-token"
            mock_config.SSO_TOKEN_ENDPOINT = "https://test.example.com/token"

            setup_credentials(mcp_server_config, logger)

        missing_cred_calls = [
            call for call in logger.error.call_args_list if "Service account credentials are required" in str(call)
        ]
        assert missing_cred_calls == []

    def test_refresh_token_without_client_id_uses_rhsm_api_default(self):
        """InsightsOAuth2Client should default client_id to rhsm-api for refresh tokens."""
        client = InsightsClient(
            api_path="/api/inventory/v1",
            client_id=None,
            refresh_token="test-refresh-token",
        )

        assert isinstance(client.client, InsightsOAuth2Client)
        assert client.client.client_id == "rhsm-api"
