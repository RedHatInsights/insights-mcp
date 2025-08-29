"""General-purpose Insights MCP client and utilities."""

import os
from importlib.metadata import PackageNotFoundError, version

# Try to get version from package metadata
try:
    __version__ = version("insights-mcp")
except PackageNotFoundError:
    # Running in development or from source
    __version__ = "0.0.0-dev"

# Allow environment variable override for container builds
__version__ = os.environ.get("INSIGHTS_MCP_VERSION", __version__)
