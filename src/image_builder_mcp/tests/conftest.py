"""
Conftest for image_builder_mcp tests - re-exports fixtures from top-level tests.
"""

# Import directly from tests since pytest now knows where to find packages
from tests.conftest import (
    test_agent,
    guardian_agent,
    default_response_size,
    test_client_credentials,
    mock_http_headers,
    mcp_server_thread,
    verbose_logger,
)

# Make the fixtures available for import
__all__ = [
    "test_agent",
    "guardian_agent",
    "default_response_size",
    "test_client_credentials",
    "mock_http_headers",
    "mcp_server_thread",
    "verbose_logger",
]
