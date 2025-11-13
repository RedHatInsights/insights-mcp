"""MCP server implementation for Red Hat Insights integration.

This module provides a FastMCP-based server class for integrating with Red Hat Insights APIs.
It handles authentication, client initialization, and provides a foundation for building
Insights-specific MCP tools and resources.
"""

import asyncio
from typing import Any

from fastmcp import FastMCP

from insights_mcp.client import (
    INSIGHTS_BASE_URL_PROD,
    INSIGHTS_TOKEN_ENDPOINT_PROD,
    InsightsClient,
)


class InsightsMCP(FastMCP):
    """MCP server class for Red Hat Insights integration.

    This class extends FastMCP to provide specialized functionality for interacting
    with Red Hat Insights APIs. It manages authentication, client initialization,
    and provides a base for implementing Insights-specific tools and resources.

    Attributes:
        api_path: The API path for Insights endpoints
        toolset_name: Name of the toolset being used
        headers: Additional HTTP headers for requests
        insights_client: Client instance for making Insights API calls
    """

    def __init__(  # pylint: disable=too-many-arguments
        self,
        name: str,
        toolset_name: str,
        api_path: str,
        *,
        headers: dict[str, str] | None = None,
        instructions: str | None = None,
        **settings: Any,
    ):
        """Initialize the InsightsMCP server.

        Args:
            name: Name of the MCP server
            toolset_name: Name of the toolset being used
            api_path: API path for Insights endpoints
            headers: Optional additional HTTP headers for requests
            instructions: Optional instructions for the MCP server
            **settings: Additional settings passed to FastMCP
        """
        super().__init__(name=name, instructions=instructions, **settings)
        self.api_path = api_path
        self.toolset_name = toolset_name
        self.headers = headers or {}
        # initialize with unauthenticated client
        self.insights_client = InsightsClient(api_path=self.api_path)

    def init_insights_client(  # pylint: disable=too-many-arguments
        self,
        *,
        base_url: str = INSIGHTS_BASE_URL_PROD,
        client_id: str | None = None,
        client_secret: str | None = None,
        refresh_token: str | None = None,
        proxy_url: str | None = None,
        headers: dict[str, str] | None = None,
        oauth_enabled: bool = False,
        mcp_transport: str | None = None,
        token_endpoint: str = INSIGHTS_TOKEN_ENDPOINT_PROD,
    ):
        """Initialize the authenticated Insights client.

        This method sets up an authenticated InsightsClient instance for making
        API calls to Red Hat Insights. Either refresh_token or client_secret
        must be provided unless oauth_enabled is True.

        Args:
            base_url: Base URL for the Insights API
            client_id: OAuth client ID for authentication
            client_secret: OAuth client secret for authentication
            refresh_token: OAuth refresh token for authentication
            proxy_url: Optional proxy URL for requests
            headers: Optional additional HTTP headers
            oauth_enabled: Whether OAuth authentication is enabled
            mcp_transport: Optional MCP transport configuration

        Raises:
            ValueError: If authentication credentials are not provided
        """
        # merge headers with self.headers
        if headers is not None:
            self.headers.update(headers)

        self.insights_client = InsightsClient(  # pylint: disable=duplicate-code
            api_path=self.api_path,
            base_url=base_url,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            proxy_url=proxy_url,
            headers=self.headers,
            oauth_enabled=oauth_enabled,
            mcp_transport=mcp_transport,
            token_endpoint=token_endpoint,
        )

    def register_tools(self) -> None:
        """Register the tools for the MCP server.

        This method is implemented by the MCP server to register the tools for the MCP server.
        """
        raise NotImplementedError("MCP server does not implement register_tools()")

    def remove_non_readonly_tools(self, readonly: bool = False):
        """Remove tools with readOnlyHint: False from the MCP server.

        Args:
            readonly: If True, remove non-readonly tools. If False, do nothing.
        """
        if not readonly:
            return

        tools = asyncio.run(self._tool_manager.get_tools())
        tools_to_remove = [
            tool_name
            for tool_name, tool in tools.items()
            if (
                hasattr(tool, "annotations")
                and tool.annotations
                and hasattr(tool.annotations, "readOnlyHint")
                and tool.annotations.readOnlyHint is False
            )
        ]

        for tool_name in tools_to_remove:
            self.remove_tool(tool_name)
