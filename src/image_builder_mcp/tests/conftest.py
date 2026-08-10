"""
Conftest for image_builder_mcp tests - re-exports fixtures from top-level tests.
"""

import os
from contextlib import contextmanager
from unittest.mock import patch

import pytest

from image_builder_mcp import ImageBuilderMCP
from insights_mcp.mcp_subprocess import cleanup_server_process, start_insights_mcp_server

# Import directly from tests since pytest now knows where to find packages
from tests.conftest import (
    TEST_BLUEPRINT_UUID,
    TEST_CLIENT_ID,
    TEST_CLIENT_SECRET,
    assert_api_error_result,
    assert_empty_response,
    assert_instruction_in_result,
    create_mcp_server,
    create_mock_client,
    default_response_size,
    guardian_agent,
    llm_api_context,
    mcp_tools,
    mock_http_headers,
    setup_toolset_mock,
    test_agent,
    test_client_credentials,
    verbose_logger,
)


@pytest.fixture(scope="session")
def mcp_server_url(request):
    """Start MCP server with only the image-builder toolset for LLM integration tests."""
    transport = getattr(request, "param", "http")
    if hasattr(request.node, "callspec") and "transport" in request.node.callspec.params:
        transport = request.node.callspec.params["transport"]

    server_url, server_process = start_insights_mcp_server(transport, toolset="image-builder")

    try:
        yield server_url
    finally:
        cleanup_server_process(server_process)


@pytest.fixture
def imagebuilder_mcp_server():
    """Create ImageBuilder MCP server for tests."""
    return create_mcp_server(ImageBuilderMCP)


@pytest.fixture
def imagebuilder_mock_client():
    """Create a mock InsightsClient for ImageBuilder tests."""
    return create_mock_client(api_path="api/v1/image-builder")


@contextmanager
def setup_imagebuilder_watermark_disabled(mcp_server, mock_client):
    """Context manager for disabling watermarks in ImageBuilder tests."""
    with (
        patch.object(mcp_server, "insights_client", mock_client),
        patch.dict(os.environ, {"IMAGE_BUILDER_MCP_DISABLE_DESCRIPTION_WATERMARK": "true"}),
    ):
        yield None  # No headers needed for image builder architecture


# pylint: disable=duplicate-code  # Test fixture patterns are similar across toolsets
# Make the fixtures available for import
__all__ = [
    "assert_api_error_result",
    "assert_empty_response",
    "assert_instruction_in_result",
    "create_mcp_server",
    "create_mock_client",
    "default_response_size",
    "guardian_agent",
    "llm_api_context",
    "imagebuilder_mcp_server",
    "imagebuilder_mock_client",
    "mcp_server_url",
    "mcp_tools",
    "mock_http_headers",
    "setup_toolset_mock",
    "setup_imagebuilder_watermark_disabled",
    "test_agent",
    "test_client_credentials",
    "TEST_BLUEPRINT_UUID",
    "TEST_CLIENT_ID",
    "TEST_CLIENT_SECRET",
    "verbose_logger",
]
