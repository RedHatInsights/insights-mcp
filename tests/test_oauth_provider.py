"""Unit tests for OAuth provider creation.

This module tests the create_oauth_provider() function which creates
FastMCP OIDCProxy instances for OAuth authentication.
"""

# pylint: disable=redefined-outer-name
# Pytest fixtures are injected as function parameters, which pylint
# incorrectly flags as redefining names from outer scope.

import importlib
import os
from unittest.mock import Mock, patch

import pytest

from insights_mcp import config as config_module
from insights_mcp.oauth import create_oauth_provider
from tests.oauth_utils import create_oauth_test_environment

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def oauth_enabled_env():
    """Environment variables for OAuth enabled mode.

    Returns:
        Dictionary of environment variables for OAUTH_ENABLED=True mode

    Example:
        >>> def test_oauth_env(oauth_enabled_env):
        ...     with patch.dict(os.environ, oauth_enabled_env):
        ...         # Test OAuth-enabled code
    """
    return create_oauth_test_environment(
        oauth_enabled=True,
        sso_client_id="test-sso-client",
        sso_client_secret="test-sso-secret",
    )


@pytest.fixture
def mock_oidc_proxy():
    """Mock OIDCProxy for testing."""
    with patch("insights_mcp.oauth.OIDCProxy") as mock_oidc:
        mock_oidc.return_value = Mock()
        yield mock_oidc


@pytest.fixture
def reload_config():
    """Reload config module to pick up environment variable changes."""

    def _reload():
        importlib.reload(config_module)

    return _reload


class TestCreateOAuthProviderBasic:
    """Test basic OAuth provider creation."""

    def _assert_required_scopes(self, call_args):
        """Assert that all required scopes are present."""
        required_scopes = call_args["required_scopes"]
        assert "openid" in required_scopes
        assert "api.console" in required_scopes
        assert "api.ocm" in required_scopes
        assert len(required_scopes) == 3

    def test_create_with_explicit_params(self, mock_oidc_proxy):
        """Test provider creation with explicit parameters."""
        provider = create_oauth_provider(
            client_id="test-sso-client", client_secret="test-sso-secret", mcp_host="localhost", mcp_port=8000
        )

        assert provider is not None
        mock_oidc_proxy.assert_called_once()

        call_args = mock_oidc_proxy.call_args[1]
        assert call_args["client_id"] == "test-sso-client"
        assert call_args["client_secret"] == "test-sso-secret"
        assert call_args["base_url"] == "http://localhost:8000"
        # Required scopes
        self._assert_required_scopes(call_args)
        # Config URL
        assert "config_url" in call_args
        assert "openid-configuration" in call_args["config_url"]

    def test_create_with_env_vars(self, oauth_enabled_env, mock_oidc_proxy, reload_config):
        """Test provider creation from environment variables."""
        with patch.dict(os.environ, {"SSO_OAUTH_TIMEOUT_SECONDS": "60", **oauth_enabled_env}):
            reload_config()

            # Explicit client ID overrides environment variables
            provider = create_oauth_provider(client_id="explicit-client")

            assert provider is not None
            mock_oidc_proxy.assert_called_once()

            call_args = mock_oidc_proxy.call_args[1]
            assert call_args["client_id"] == "explicit-client"
            assert call_args["client_secret"] == "test-sso-secret"
            # Timeout seconds
            assert "timeout_seconds" in call_args
            assert call_args["timeout_seconds"] == 60

    @pytest.mark.parametrize(
        "host,port,expected_url",
        [
            ("example.com", 9000, "http://example.com:9000"),
            (None, None, "http://localhost:8000"),
        ],
    )
    def test_base_url_construction(self, mock_oidc_proxy, host, port, expected_url):
        """Test base URL construction with custom and default values."""
        kwargs = {"client_id": "test-client", "client_secret": "test-secret"}
        if host:
            kwargs["mcp_host"] = host
        if port:
            kwargs["mcp_port"] = port

        provider = create_oauth_provider(**kwargs)

        assert provider is not None
        mock_oidc_proxy.assert_called_once()

        call_args = mock_oidc_proxy.call_args[1]
        assert call_args["base_url"] == expected_url

    @pytest.mark.parametrize(
        "exception_class,error_message",
        [
            (ValueError, "Invalid configuration"),
            (ConnectionError, "Cannot connect to SSO"),
        ],
    )
    def test_create_raises_on_failure(self, exception_class, error_message):
        """Test provider creation fails when OIDCProxy raises exception."""
        with patch("insights_mcp.oauth.OIDCProxy") as mock_oidc:
            mock_oidc.side_effect = exception_class(error_message)

            with pytest.raises(exception_class, match=error_message):
                create_oauth_provider(client_id="test-client", client_secret="test-secret")
