"""
Conftest for image_builder_mcp tests - re-exports fixtures from top-level tests.
"""

import os
from contextlib import contextmanager
from unittest.mock import patch

import pytest

from image_builder_mcp import ImageBuilderMCP

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
    mcp_server_url,
    mcp_tools,
    mock_http_headers,
    setup_mcp_mock,
    test_agent,
    test_client_credentials,
    verbose_logger,
)


@pytest.fixture
def imagebuilder_mcp_server():
    """Create ImageBuilder MCP server for tests."""
    return create_mcp_server(ImageBuilderMCP)


@pytest.fixture
def imagebuilder_mock_client():
    """Create a mock InsightsClient for ImageBuilder tests."""
    return create_mock_client(api_path="api/v1/image-builder")


@contextmanager
def setup_imagebuilder_mock(mcp_server, mock_client, mock_response=None, side_effect=None):
    """Context manager for setting up ImageBuilder mock patterns.
    Uses self.insights_client directly from InsightsMCP base class
    """
    # pylint: disable=duplicate-code  # Similar mock setup patterns across toolsets
    # Set up mock responses
    if side_effect:
        mock_client.get.side_effect = side_effect
        mock_client.post.side_effect = side_effect
        mock_client.put.side_effect = side_effect
    elif mock_response is not None:
        mock_client.get.return_value = mock_response
        mock_client.post.return_value = mock_response
        mock_client.put.return_value = mock_response

    # Mock the insights_client directly on the server instance
    with patch.object(mcp_server, "insights_client", mock_client):
        yield None  # No headers needed for image builder architecture


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
    "imagebuilder_mcp_server",
    "imagebuilder_mock_client",
    "mcp_server_url",
    "mcp_tools",
    "mock_http_headers",
    "setup_imagebuilder_mock",
    "setup_imagebuilder_watermark_disabled",
    "setup_mcp_mock",
    "test_agent",
    "test_client_credentials",
    "TEST_BLUEPRINT_UUID",
    "TEST_CLIENT_ID",
    "TEST_CLIENT_SECRET",
    "verbose_logger",
]
