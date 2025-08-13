"""Test suite for authentication-related functionality."""

from unittest.mock import patch
import pytest

# Clean import - no sys.path.insert needed with proper package structure!
from image_builder_mcp import ImageBuilderMCP
import image_builder_mcp.server as image_builder_mcp


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

        # Setup mocks - no credentials
        with patch.object(image_builder_mcp, "get_http_headers") as mock_headers:
            mock_headers.return_value = {}

            # Call the method
            method = getattr(mcp_server, function_name)
            result = await method(**kwargs)

            # Should return authentication error
            # The actual implementation makes API calls and gets 401 errors when no auth is provided
            assert result.startswith("Error:")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("function_name,kwargs", AUTH_FUNCTIONS)
    async def test_function_no_auth_error_message(self, function_name, kwargs):
        """Test that functions return the no_auth_error() message when authentication is missing."""
        # Create MCP server without default credentials
        mcp_server = ImageBuilderMCP()
        mcp_server.init_insights_client(
            client_id=None,
            client_secret=None,
            oauth_enabled=False,
        )
        mcp_server.register_tools()

        # Test default transport mode
        with patch.object(image_builder_mcp, "get_http_headers") as mock_headers:
            mock_headers.return_value = {}  # No auth headers

            method = getattr(mcp_server, function_name)
            result = await method(**kwargs)

            # Check for relevant parts of the no_auth_error message for default transport
            assert "Tell the user" in result
            assert "INSIGHTS_CLIENT_ID" in result
            assert "INSIGHTS_CLIENT_SECRET" in result
            assert "mcp.json config" in result
            assert "Error: Client ID is required to access the Image Builder API" in result

    @pytest.mark.asyncio
    @pytest.mark.parametrize("function_name,kwargs", AUTH_FUNCTIONS)
    async def test_function_no_auth_error_message_sse_transport(self, function_name, kwargs):
        """Test that functions return the no_auth_error() message for SSE transport.

        Tests the case when authentication is missing.
        """
        # Create MCP server with SSE transport
        mcp_server = ImageBuilderMCP()
        mcp_server.init_insights_client(
            client_id=None,
            client_secret=None,
            oauth_enabled=False,
            mcp_transport="sse",
        )
        mcp_server.register_tools()

        with patch.object(image_builder_mcp, "get_http_headers") as mock_headers:
            mock_headers.return_value = {}  # No auth headers

            method = getattr(mcp_server, function_name)
            result = await method(**kwargs)

            # Check for relevant parts of the no_auth_error message for SSE transport
            assert "Tell the user" in result
            assert "header variables" in result
            assert "insights-client-id" in result
            assert "insights-client-secret" in result
            assert "Error: Client ID is required to access the Image Builder API" in result

    @pytest.mark.asyncio
    @pytest.mark.parametrize("function_name,kwargs", AUTH_FUNCTIONS)
    async def test_function_no_auth_error_message_http_transport(self, function_name, kwargs):
        """Test that functions return the no_auth_error() message for HTTP transport.

        Tests the case when authentication is missing.
        """
        # Create MCP server with HTTP transport
        mcp_server = ImageBuilderMCP()
        mcp_server.init_insights_client(
            client_id=None,
            client_secret=None,
            oauth_enabled=False,
            mcp_transport="http",
        )
        mcp_server.register_tools()

        with patch.object(image_builder_mcp, "get_http_headers") as mock_headers:
            mock_headers.return_value = {}  # No auth headers

            method = getattr(mcp_server, function_name)
            result = await method(**kwargs)

            # Check for relevant parts of the no_auth_error message for HTTP transport
            assert "Tell the user" in result
            assert "header variables" in result
            assert "insights-client-id" in result
            assert "insights-client-secret" in result
            assert "Error: Client ID is required to access the Image Builder API" in result
