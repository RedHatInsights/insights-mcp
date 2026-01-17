"""Test suite for authentication-related functionality."""

from unittest.mock import patch

import pytest
from authlib.integrations.httpx_client import OAuthError

# Clean import - no sys.path.insert needed with proper package structure!
from image_builder_mcp import ImageBuilderMCP

# Brand test cases for HTTP/SSE transports - only need to verify id header
BRAND_HEADER_TEST_CASES = ["insights-client-id", "lightspeed-client-id"]
BRAND_HEADER_IDS = ["insights", "red-hat-lightspeed"]

# Brand test cases for stdio transport - only need to verify id env
BRAND_ENV_TEST_CASES = ["INSIGHTS_CLIENT_ID", "LIGHTSPEED_CLIENT_ID"]
BRAND_ENV_IDS = ["insights", "red-hat-lightspeed"]


class TestAuthentication:
    """Test suite for authentication-related functionality."""

    # List of functions to test for authentication (excluding get_openapi)
    # TBD: change to dynamically getting from MCP server
    AUTH_FUNCTIONS = [
        ("create_blueprint", {"data": {"name": "test", "description": "test"}}),
        ("get_blueprints", {"limit": 7, "offset": 0, "search_string": ""}),
        ("get_blueprint_details", {"blueprint_identifier": "12345678-1234-1234-1234-123456789012"}),
        ("get_composes", {"limit": 7, "offset": 0, "search_string": ""}),
        ("get_compose_details", {"compose_identifier": "12345678-1234-1234-1234-123456789012"}),
        ("blueprint_compose", {"blueprint_uuid": "12345678-1234-1234-1234-123456789012"}),
    ]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("function_name,kwargs", AUTH_FUNCTIONS)
    async def test_function_no_auth(self, function_name, kwargs):
        """Test that functions without authentication return error."""
        mcp_server = ImageBuilderMCP()
        mcp_server.init_insights_client(
            client_id="test-client-id",
            client_secret="test-client-secret",
            oauth_enabled=False,
        )
        mcp_server.register_tools()

        # Mock fetch_token to simulate OAuth error without making real network calls
        async def mock_fetch_token(*args, **kwargs):
            raise OAuthError(error="invalid_client", description="Invalid client or Invalid client credentials")

        with patch.object(mcp_server.insights_client.client, "fetch_token", new=mock_fetch_token):
            # Call the method
            method = getattr(mcp_server, function_name)
            result = await method(**kwargs)

            # Should return authentication error
            # The mocked implementation raises OAuthError which gets caught and formatted
            assert "Invalid client or Invalid client credentials" in result
            assert "[INSTRUCTION]" in result

    @pytest.mark.asyncio
    @pytest.mark.parametrize("function_name,kwargs", AUTH_FUNCTIONS)
    @pytest.mark.parametrize("expected_id_env", BRAND_ENV_TEST_CASES, ids=BRAND_ENV_IDS)
    async def test_function_no_auth_error_message(self, function_name, kwargs, expected_id_env, monkeypatch):
        """Test that functions return the no_auth_error() message when authentication is missing.

        Tests that the correct branded env variable names appear in the error message for stdio transport.
        """
        # Patch the brand env variable name in the client module
        monkeypatch.setattr("insights_mcp.client.BRAND_CLIENT_ID_ENV", expected_id_env)

        # Create MCP server without default credentials (default is stdio transport)
        mcp_server = ImageBuilderMCP()
        mcp_server.init_insights_client(
            client_id=None,
            client_secret=None,
            oauth_enabled=False,
        )
        mcp_server.register_tools()

        method = getattr(mcp_server, function_name)
        result = await method(**kwargs)

        # Verify branded env variable name appears in error message
        assert "[INSTRUCTION] There seems to be a problem with the request." in result
        assert "authentication problem" in result
        assert expected_id_env in result

    @pytest.mark.asyncio
    @pytest.mark.parametrize("function_name,kwargs", AUTH_FUNCTIONS)
    @pytest.mark.parametrize("expected_id_header", BRAND_HEADER_TEST_CASES, ids=BRAND_HEADER_IDS)
    async def test_function_no_auth_error_message_sse_transport(
        self, function_name, kwargs, expected_id_header, monkeypatch
    ):
        """Test that functions return the no_auth_error() message for SSE transport.

        Tests that the correct branded header name appears in the error message.
        """
        # Patch the brand header value in the client module
        monkeypatch.setattr("insights_mcp.client.BRAND_CLIENT_ID_HEADER", expected_id_header)

        # Create MCP server with SSE transport
        mcp_server = ImageBuilderMCP()
        mcp_server.init_insights_client(
            client_id=None,
            client_secret=None,
            oauth_enabled=False,
            mcp_transport="sse",
        )
        mcp_server.register_tools()

        method = getattr(mcp_server, function_name)
        result = await method(**kwargs)

        # Verify branded header appears in error message
        assert "[INSTRUCTION] There seems to be a problem with the request." in result
        assert "authentication problem" in result
        assert expected_id_header in result

    @pytest.mark.asyncio
    @pytest.mark.parametrize("function_name,kwargs", AUTH_FUNCTIONS)
    @pytest.mark.parametrize("expected_id_header", BRAND_HEADER_TEST_CASES, ids=BRAND_HEADER_IDS)
    async def test_function_no_auth_error_message_http_transport(
        self, function_name, kwargs, expected_id_header, monkeypatch
    ):
        """Test that functions return the no_auth_error() message for HTTP transport.

        Tests that the correct branded header name appears in the error message.
        """
        # Patch the brand header value in the client module
        monkeypatch.setattr("insights_mcp.client.BRAND_CLIENT_ID_HEADER", expected_id_header)

        # Create MCP server with HTTP transport
        mcp_server = ImageBuilderMCP()
        mcp_server.init_insights_client(
            client_id=None,
            client_secret=None,
            oauth_enabled=False,
            mcp_transport="http",
        )
        mcp_server.register_tools()

        method = getattr(mcp_server, function_name)
        result = await method(**kwargs)

        # Verify branded header appears in error message
        assert "[INSTRUCTION] There seems to be a problem with the request." in result
        assert "authentication problem" in result
        assert expected_id_header in result
