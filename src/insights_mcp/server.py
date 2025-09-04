"""Main Insights MCP server that mounts multiple Red Hat service servers."""

import argparse
import asyncio
import os
import sys
from logging import DEBUG, getLogger
from typing import Any

import uvicorn
from fastmcp import FastMCP

from advisor_mcp.server import mcp_server as AdvisorMCP
from content_sources_mcp.server import mcp as ContentSourcesMCP
from image_builder_mcp.server import mcp_server as ImageBuilderMCP
from insights_mcp import __version__
from insights_mcp.mcp import INSIGHTS_BASE_URL, InsightsMCP
from insights_mcp.oauth import Middleware
from inventory_mcp.server import mcp as InventoryMCP
from rbac_mcp.server import mcp as RbacMCP
from remediations_mcp.server import mcp as RemediationsMCP
from vulnerability_mcp.server import mcp as VulnerabilityMCP

MCPS: list[InsightsMCP] = [ImageBuilderMCP, VulnerabilityMCP, RemediationsMCP, AdvisorMCP, InventoryMCP, ContentSourcesMCP, RbacMCP]


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

            self.mount(mcp, prefix=f"{mcp.toolset_name}_")


def get_instructions(allowed_mcps: list[str]) -> str:
    """Get instructions from MCP server."""
    instructions_parts = []
    for mcp in MCPS:
        if mcp.toolset_name not in allowed_mcps:
            continue
        if hasattr(mcp, "instructions") and mcp.instructions:
            instructions_parts.append(f"## {mcp.name}\n\n{mcp.instructions}")
    return "\n\n".join(instructions_parts)


def print_toolset_help_and_exit(args: argparse.Namespace):
    """Print toolset help and exit."""
    if args.toolset_help:
        print("# All available toolsets")
        for mcp in MCPS:
            print(f"\n## {mcp.toolset_name}")

            # Register tools to ensure they are available
            try:
                mcp.register_tools()
            except NotImplementedError:
                pass  # Some MCPs might not implement register_tools

            # Get and display tools
            tools = None
            try:
                tools = asyncio.run(mcp.get_tools())
            except Exception:  # pylint: disable=broad-exception-caught
                print("  Error retrieving tools")
                print()
                continue

            if not tools:
                print("  No tools available")
                print()
                continue

            for tool_name, tool in tools.items():
                title = getattr(tool, "title", None)
                description = getattr(tool, "description", None)

                # Determine title part
                title_part = None
                if title and title.strip() and title != "None":
                    title_part = title.strip()
                elif description and description.strip():
                    title_part = description.split("\n")[0].strip()

                # Format: tool_name or tool_name: title
                if title_part:
                    display_text = f"`{tool_name}`: {title_part}"
                else:
                    display_text = f"`{tool_name}`"

                # Truncate very long lines
                if len(display_text) > 100:
                    display_text = display_text[:97] + "…"

                print(f"- {display_text}")

        sys.exit(0)


def main():  # pylint: disable=too-many-statements,too-many-locals
    """Main entry point for the Insights MCP server."""
    available_toolsets = f"all, {', '.join(mcp.toolset_name for mcp in MCPS)}"
    toolset_help = f"Comma-separated list of toolsets to use. Available toolsets: {available_toolsets} (default: all)"

    parser = argparse.ArgumentParser(description="Run Insights MCP server.")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--stage", action="store_true", help="Use stage API instead of production API")
    parser.add_argument("--toolset", type=str, help=toolset_help)
    parser.add_argument("--toolset-help", action="store_true", help="Show toolset details of all toolsets")

    # Create subparsers for different transport modes
    subparsers = parser.add_subparsers(dest="transport", help="Transport mode")

    # stdio subcommand (default)
    subparsers.add_parser("stdio", help="Use stdio transport (default)")

    # sse subcommand
    sse_parser = subparsers.add_parser("sse", help="Use SSE transport")
    sse_parser.add_argument("--host", default="127.0.0.1", help="Host for SSE transport (default: 127.0.0.1)")
    sse_parser.add_argument("--port", type=int, default=9000, help="Port for SSE transport (default: 9000)")

    # http subcommand
    http_parser = subparsers.add_parser("http", help="Use HTTP streaming transport")
    http_parser.add_argument("--host", default="127.0.0.1", help="Host for HTTP transport (default: 127.0.0.1)")
    http_parser.add_argument("--port", type=int, default=8000, help="Port for HTTP transport (default: 8000)")

    args = parser.parse_args()

    print_toolset_help_and_exit(args)

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

    logger = getLogger("InsightsMCPServer")

    if args.debug:  # FIXME: make common logging setup
        getLogger("ImageBuilderMCP").setLevel(DEBUG)
        getLogger("InsightsClientBase").setLevel(DEBUG)
        getLogger("InsightsClient").setLevel(DEBUG)
        getLogger("ImageBuilderOAuthMiddleware").setLevel(DEBUG)
        logger.info("Debug mode enabled")

    oauth_enabled = os.getenv("OAUTH_ENABLED", "false").lower() == "true"
    toolset = args.toolset or os.getenv("INSIGHTS_TOOLSET", "all")

    if toolset == "all":
        toolset_list = [mcp.toolset_name for mcp in MCPS]
    else:
        toolset_list = [t.strip() for t in toolset.split(",")]

    logger.warning(
        "Starting Insights MCP %s (%s) with toolsets: %s",
        __version__,
        args.transport,
        ", ".join(toolset_list),
    )

    instructions = get_instructions(toolset_list)

    # Create and run the MCP server
    mcp_server = InsightsMCPServer(
        base_url=INSIGHTS_BASE_URL if not args.stage else os.getenv("INSIGHTS_BASE_URL"),
        client_id=client_id,
        client_secret=client_secret,
        refresh_token=os.getenv("INSIGHTS_REFRESH_TOKEN"),
        proxy_url=proxy_url,
        oauth_enabled=oauth_enabled,
        mcp_transport=args.transport,
        instructions=instructions,
    )

    mcp_server.register_mcps(toolset_list)

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
                logger.fatal("OAUTH_CLIENT environment variable is required for OAuth-enabled HTTP transport")
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
