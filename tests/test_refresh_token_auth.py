"""Tests for refresh-token authentication credential handling."""

import importlib
from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest

import insights_mcp.config as config_module
from insights_mcp.client import InsightsClient, InsightsOAuth2Client
from insights_mcp.server import setup_credentials


def _reload_config(monkeypatch: pytest.MonkeyPatch, **env: str | None):
    """Reload config module with the given environment variables."""
    for key, value in env.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)
    return importlib.reload(config_module)


class TestRefreshTokenAuth:
    """Test credential normalization and client defaults for refresh-token authentication."""

    def test_setup_credentials_passes_through_none_client_id_when_refresh_token_set(self):
        """Unset INSIGHTS_CLIENT_ID stays None so the rhsm-api default can apply."""
        mcp_server_config = {"oauth_enabled": False, "mcp_transport": "stdio"}
        logger = MagicMock()

        with patch("insights_mcp.server.config") as mock_config:
            mock_config.INSIGHTS_CLIENT_ID = None
            mock_config.INSIGHTS_CLIENT_SECRET = None
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
            mock_config.INSIGHTS_CLIENT_ID = None
            mock_config.INSIGHTS_CLIENT_SECRET = None
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


class TestLightspeedRefreshTokenConfig:
    """Test LIGHTSPEED_REFRESH_TOKEN fallback in config."""

    @pytest.fixture(autouse=True)
    def _restore_config_module(self) -> Iterator[None]:
        """Reload config after each test so env-driven reloads do not leak state.

        monkeypatch restores os.environ first (same-scope fixtures tear down in
        reverse setup order), then this reload reads the original environment.
        """
        yield
        importlib.reload(config_module)

    def test_empty_credential_env_vars_become_none(self, monkeypatch: pytest.MonkeyPatch):
        """Unset or empty credential env vars are stored as None, not empty strings."""
        reloaded = _reload_config(
            monkeypatch,
            INSIGHTS_CLIENT_ID="",
            INSIGHTS_CLIENT_SECRET="",
            INSIGHTS_REFRESH_TOKEN="",
            LIGHTSPEED_CLIENT_ID=None,
            LIGHTSPEED_CLIENT_SECRET=None,
            LIGHTSPEED_REFRESH_TOKEN=None,
        )

        assert reloaded.INSIGHTS_CLIENT_ID is None
        assert reloaded.INSIGHTS_CLIENT_SECRET is None
        assert reloaded.INSIGHTS_REFRESH_TOKEN is None

    def test_lightspeed_refresh_token_used_when_insights_unset(self, monkeypatch: pytest.MonkeyPatch):
        """LIGHTSPEED_REFRESH_TOKEN is used when INSIGHTS_REFRESH_TOKEN is unset."""
        reloaded = _reload_config(
            monkeypatch,
            INSIGHTS_REFRESH_TOKEN=None,
            LIGHTSPEED_REFRESH_TOKEN="lightspeed-refresh-token",
        )

        assert reloaded.INSIGHTS_REFRESH_TOKEN == "lightspeed-refresh-token"

    def test_insights_refresh_token_takes_precedence(self, monkeypatch: pytest.MonkeyPatch):
        """INSIGHTS_REFRESH_TOKEN wins when both env vars are set."""
        reloaded = _reload_config(
            monkeypatch,
            INSIGHTS_REFRESH_TOKEN="insights-refresh-token",
            LIGHTSPEED_REFRESH_TOKEN="lightspeed-refresh-token",
        )

        assert reloaded.INSIGHTS_REFRESH_TOKEN == "insights-refresh-token"

    def test_lightspeed_refresh_token_with_insights_client_id_set(self, monkeypatch: pytest.MonkeyPatch):
        """LIGHTSPEED_REFRESH_TOKEN works even when INSIGHTS_CLIENT_ID is set."""
        reloaded = _reload_config(
            monkeypatch,
            INSIGHTS_CLIENT_ID="rhsm-api",
            INSIGHTS_REFRESH_TOKEN=None,
            LIGHTSPEED_REFRESH_TOKEN="lightspeed-refresh-token",
        )

        assert reloaded.INSIGHTS_CLIENT_ID == "rhsm-api"
        assert reloaded.INSIGHTS_REFRESH_TOKEN == "lightspeed-refresh-token"
