"""Main Insights MCP server that mounts multiple Red Hat service servers."""
import argparse
import logging
import os
import sys
from typing import Any

import uvicorn
from fastmcp import FastMCP

from image_builder_mcp.server import mcp_server as ImageBuilderMCP
from insights_mcp.mcp import INSIGHTS_BASE_URL, InsightsMCP
from insights_mcp.oauth import Middleware

MCPS: list[InsightsMCP] = [ImageBuilderMCP]


class InsightsMCPServer(FastMCP):
    """Unified MCP server that mounts multiple Red Hat Insights service servers.

    This server acts as a container for multiple specialized MCP servers,
    allowing them to be accessed through a single endpoint. It handles
    authentication and configuration for all mounted servers.

    Args:
        name: Name of the MCP server
        instructions: Optional instructions for the server
        base_url: Base URL for Red Hat Insights APIs
        client_id: OAuth client ID for authentication
        client_secret: OAuth client secret for authentication
        refresh_token: OAuth refresh token for authentication
        proxy_url: Optional proxy URL for requests
        oauth_enabled: Whether OAuth authentication is enabled
        mcp_transport: MCP transport type for error handling
        **settings: Additional settings passed to parent class
    """

    def __init__(  # pylint: disable=too-many-arguments
        self,
        name: str | None = None,
        instructions: str | None = None,
        *,
        base_url: str = INSIGHTS_BASE_URL,
        client_id: str | None = None,
        client_secret: str | None = None,
        refresh_token: str | None = None,
        proxy_url: str | None = None,
        oauth_enabled: bool = False,
        mcp_transport: str | None = None,
        **settings: Any,
    ):
        name = name or "Red Hat Insights"
        super().__init__(
            name=name,
            instructions=instructions,
            **settings,
        )
        self.base_url = base_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.proxy_url = proxy_url
        self.oauth_enabled = oauth_enabled
        self.mcp_transport = mcp_transport

    def register_mcps(self, allowed_mcps: list[str]):
        """Register and mount allowed MCP servers.

        Args:
            allowed_mcps: List of MCP server names to register and mount
        """
        for mcp in MCPS:
            if mcp.toolset_name not in allowed_mcps:
                continue

            mcp.init_insights_client(
                base_url=self.base_url,
                client_id=self.client_id,
                client_secret=self.client_secret,
                refresh_token=self.refresh_token,
                proxy_url=self.proxy_url,
                headers=mcp.headers,
                oauth_enabled=self.oauth_enabled,
                mcp_transport=self.mcp_transport,
            )
            try:
                mcp.register_tools()
            except NotImplementedError:
                pass  # TBD log debug message

            self.mount(mcp)


def main():  # pylint: disable=too-many-statements
    """Main entry point for the Insights MCP server."""
    parser = argparse.ArgumentParser(
        description="Run Insights MCP server.")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--stage", action="store_true", help="Use stage API instead of production API")
    parser.add_argument("--toolset", type=str, help="Comma-separated list of toolsets to use. Available toolsets: " +
                        "all, " + ", ".join(mcp.toolset_name for mcp in MCPS) + " (default: all)")

    # Create subparsers for different transport modes
    subparsers = parser.add_subparsers(dest="transport", help="Transport mode")

    # stdio subcommand (default)
    subparsers.add_parser("stdio", help="Use stdio transport (default)")

    # sse subcommand
    sse_parser = subparsers.add_parser("sse", help="Use SSE transport")
    sse_parser.add_argument("--host", default="127.0.0.1", help="Host for SSE transport (default: 127.0.0.1)")
    sse_parser.add_argument("--port", type=int, default=9000, help="Port for SSE transport (default: 9000)")

    # http subcommand
    http_parser = subparsers.add_parser(
        "http", help="Use HTTP streaming transport")
    http_parser.add_argument("--host", default="127.0.0.1", help="Host for HTTP transport (default: 127.0.0.1)")
    http_parser.add_argument("--port", type=int, default=8000, help="Port for HTTP transport (default: 8000)")

    args = parser.parse_args()

    # Default to stdio if no subcommand is provided
    if args.transport is None:
        args.transport = "stdio"

    # Get credentials from environment variables or user input
    client_id = os.getenv("INSIGHTS_CLIENT_ID")
    client_secret = os.getenv("INSIGHTS_CLIENT_SECRET")

    proxy_url = None
    if args.stage:
        proxy_url = os.getenv("INSIGHTS_STAGE_PROXY_URL")
        if not proxy_url:
            print("Please set INSIGHTS_STAGE_PROXY_URL to access the stage API")
            print("hint: INSIGHTS_STAGE_PROXY_URL=http://yoursquidproxy…:3128")
            sys.exit(1)

    if args.debug:  # FIXME: make common logging setup
        logging.getLogger("ImageBuilderMCP").setLevel(logging.DEBUG)
        logging.getLogger("InsightsClientBase").setLevel(logging.DEBUG)
        logging.getLogger("InsightsClient").setLevel(logging.DEBUG)
        logging.getLogger("ImageBuilderOAuthMiddleware").setLevel(logging.DEBUG)
        logging.info("Debug mode enabled")

    oauth_enabled = os.getenv("OAUTH_ENABLED", "false").lower() == "true"
    toolset = args.toolset or os.getenv("INSIGHTS_TOOLSET", "all")

    # Create and run the MCP server
    mcp_server = InsightsMCPServer(
        base_url=INSIGHTS_BASE_URL if not args.stage else os.getenv("INSIGHTS_BASE_URL"),
        client_id=client_id,
        client_secret=client_secret,
        refresh_token=os.getenv("INSIGHTS_REFRESH_TOKEN"),
        proxy_url=proxy_url,
        oauth_enabled=oauth_enabled,
        mcp_transport=args.transport,
    )

    if toolset == "all":
        mcp_server.register_mcps([mcp.toolset_name for mcp in MCPS])
    else:
        mcp_server.register_mcps(toolset.split(","))

    if args.transport == "sse":
        mcp_server.run(transport="sse", host=args.host, port=args.port)
    elif args.transport == "http":
        if oauth_enabled:
            app = mcp_server.http_app(transport="http")
            self_url = os.getenv(
                "SELF_URL",
                f"http://{args.host}:{args.port}",
            )
            oauth_url = os.getenv(
                "OAUTH_URL",
                "https://sso.redhat.com/auth/realms/redhat-external",
            )
            oauth_client = os.getenv("OAUTH_CLIENT")
            if not oauth_client:
                logging.fatal("OAUTH_CLIENT environment variable is required for OAuth-enabled HTTP transport")
                sys.exit(1)

            app.add_middleware(
                Middleware,
                self_url=self_url,
                oauth_url=oauth_url,
                oauth_client=oauth_client,
            )

            # Start the application
            uvicorn.run(app, host=args.host, port=args.port)
        else:
            mcp_server.run(transport="http", host=args.host, port=args.port)
    else:
        mcp_server.run()


if __name__ == "__main__":
    main()
