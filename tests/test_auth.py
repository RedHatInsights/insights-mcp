"""Test suite for authentication-related functionality."""

import asyncio
from unittest.mock import patch

import pytest
from authlib.integrations.httpx_client import OAuthError

from image_builder_mcp import ImageBuilderMCP
from insights_mcp.errors import InsightsApiError

# Brand test cases for HTTP/SSE transports - only need to verify id header
BRAND_HEADER_TEST_CASES = ["insights-client-id", "lightspeed-client-id"]
BRAND_HEADER_IDS = ["insights", "red-hat-lightspeed"]

# Brand test cases for stdio transport - only need to verify id env
BRAND_ENV_TEST_CASES = ["INSIGHTS_CLIENT_ID", "LIGHTSPEED_CLIENT_ID"]
BRAND_ENV_IDS = ["insights", "red-hat-lightspeed"]


def _create_server(client_id="test-client-id", client_secret="test-client-secret", mcp_transport=None):
    server = ImageBuilderMCP()
    server.init_insights_client(
        client_id=client_id,
        client_secret=client_secret,
        mcp_transport=mcp_transport,
    )
    server.register_tools()
    return server


async def _assert_missing_credentials_error(mcp_server, function_name, kwargs, expected_identifier):
    """Call an MCP tool and assert it raises an auth error mentioning the expected identifier."""
    method = getattr(mcp_server, function_name)
    with pytest.raises(InsightsApiError) as exc_info:
        await method(**kwargs)

    error_message = str(exc_info.value)
    assert "[INSTRUCTION] There seems to be a problem with the request." in error_message
    assert "authentication problem" in error_message
    assert expected_identifier in error_message


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
        ("update_blueprint", {"blueprint_uuid": "12345678-1234-1234-1234-123456789012", "data": {}}),
        ("get_distributions", {}),
        ("get_org_id", {}),
    ]

    UNAUTHENTICATED_TOOLS = {"get_openapi"}

    def test_auth_functions_cover_all_tools(self):
        """Guard: fail when a new tool is added but not covered by AUTH_FUNCTIONS."""
        server = ImageBuilderMCP()
        server.register_tools()
        all_tools = {t.name for t in asyncio.run(server.list_tools())}
        tested = {name for name, _ in self.AUTH_FUNCTIONS}
        untested = all_tools - tested - self.UNAUTHENTICATED_TOOLS
        assert not untested, f"Tools missing from AUTH_FUNCTIONS: {untested}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("function_name,kwargs", AUTH_FUNCTIONS)
    async def test_function_no_auth(self, function_name, kwargs):
        """Test that functions without authentication raise InsightsApiError."""
        mcp_server = _create_server()

        async def mock_fetch_token(*args, **kwargs):
            raise OAuthError(error="invalid_client", description="Invalid client or Invalid client credentials")

        with patch.object(mcp_server.insights_client.client, "fetch_token", new=mock_fetch_token):
            method = getattr(mcp_server, function_name)
            with pytest.raises(InsightsApiError) as exc_info:
                await method(**kwargs)

            error_message = str(exc_info.value)
            assert "Invalid client or Invalid client credentials" in error_message
            assert "[INSTRUCTION]" in error_message

    @pytest.mark.asyncio
    @pytest.mark.parametrize("function_name,kwargs", AUTH_FUNCTIONS)
    @pytest.mark.parametrize("expected_id_env", BRAND_ENV_TEST_CASES, ids=BRAND_ENV_IDS)
    async def test_function_no_auth_error_message(self, function_name, kwargs, expected_id_env, monkeypatch):
        """Test auth error message when credentials are missing (stdio transport)."""
        monkeypatch.setattr("insights_mcp.client.BRAND_CLIENT_ID_ENV", expected_id_env)
        mcp_server = _create_server(client_id=None, client_secret=None)
        await _assert_missing_credentials_error(mcp_server, function_name, kwargs, expected_id_env)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("function_name,kwargs", AUTH_FUNCTIONS)
    @pytest.mark.parametrize("expected_id_header", BRAND_HEADER_TEST_CASES, ids=BRAND_HEADER_IDS)
    @pytest.mark.parametrize("transport", ["sse", "http"])
    async def test_function_no_auth_error_message_header_transport(
        self, function_name, kwargs, expected_id_header, transport, monkeypatch
    ):
        """Test auth error message for header-based transports (SSE, HTTP)."""
        monkeypatch.setattr("insights_mcp.client.BRAND_CLIENT_ID_HEADER", expected_id_header)
        mcp_server = _create_server(client_id=None, client_secret=None, mcp_transport=transport)
        await _assert_missing_credentials_error(mcp_server, function_name, kwargs, expected_id_header)
