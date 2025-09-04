"""
Conftest for content_sources_mcp tests - re-exports fixtures from top-level tests.
"""

# Import directly from tests since pytest now knows where to find packages
from tests.conftest import (
    mcp_server_url,
    mcp_tools,
)

# Make the fixtures available for import
__all__ = [
    "mcp_server_url",
    "mcp_tools",
]
