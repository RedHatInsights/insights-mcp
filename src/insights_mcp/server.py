"""Main Insights MCP server that mounts multiple Red Hat service servers."""

import argparse
import asyncio
import logging
import sys
from typing import Any

import requests
from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from advisor_mcp.server import mcp_server as AdvisorMCP
from content_sources_mcp.server import mcp as ContentSourcesMCP
from image_builder_mcp.server import mcp_server as ImageBuilderMCP
from insights_mcp import __version__
from insights_mcp import config
from insights_mcp.mcp import InsightsMCP
from insights_mcp.oauth import init_oauth_provider
from inventory_mcp.server import mcp as InventoryMCP
from planning_mcp.server import mcp as PlanningMCP
from rbac_mcp.server import mcp as RbacMCP
from remediations_mcp.server import mcp as RemediationsMCP
from rhsm_mcp.server import mcp as RhsmMCP
from vulnerability_mcp.server import mcp as VulnerabilityMCP

MCPS: list[InsightsMCP] = [
    ImageBuilderMCP,
    RhsmMCP,
    VulnerabilityMCP,
    RemediationsMCP,
    AdvisorMCP,
    InventoryMCP,
    ContentSourcesMCP,
    RbacMCP,
    PlanningMCP,
]


class InsightsMCPServer(FastMCP):  # pylint: disable=too-many-instance-attributes
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
        mcp_host: MCP server host for authentication
        mcp_port: MCP server port for authentication
        token_endpoint: Token endpoint for authentication
        **settings: Additional settings passed to parent class
    """

    def __init__(  # pylint: disable=too-many-arguments
        self,
        name: str | None = None,
        instructions: str | None = None,
        *,
        base_url: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        refresh_token: str | None = None,
        proxy_url: str | None = None,
        oauth_enabled: bool = False,
        mcp_transport: str | None = None,
        mcp_host: str | None = None,
        mcp_port: int | None = None,
        token_endpoint: str | None = None,
        **settings: Any,
    ):
        name = name or "Red Hat Insights"

        # Initialize the OAuth provider
        oauth_provider =  init_oauth_provider(
            client_id=client_id,
            client_secret=client_secret,
            mcp_host=mcp_host,
            mcp_port=mcp_port,
        ) if oauth_enabled else None

        super().__init__(
            name=name,
            instructions=instructions,
            auth=oauth_provider,
            **settings,
        )
        self.base_url = base_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.proxy_url = proxy_url
        self.oauth_enabled = oauth_enabled
        self.mcp_transport = mcp_transport
        self.token_endpoint = token_endpoint

    def register_mcps(self, allowed_mcps: list[str], readonly: bool = False):
        """Register and mount allowed MCP servers.

        Args:
            allowed_mcps: List of MCP server names to register and mount
            readonly: If True, only register read-only tools
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
                oauth_provider=self.auth,
                mcp_transport=self.mcp_transport,
                token_endpoint=self.token_endpoint,
            )
            try:
                mcp.register_tools()
            except NotImplementedError:
                pass  # Some MCPs don't implement register_tools

            mcp.remove_non_readonly_tools(readonly=readonly)

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


def get_latest_release_tag() -> str:
    """Get the latest release tag from github."""
    # https://github.com/RedHatInsights/insights-mcp/releases
    # rather use the api to get the latest release tag
    response = requests.get("https://api.github.com/repos/RedHatInsights/insights-mcp/releases/latest", timeout=30)
    response.raise_for_status()
    return response.json()["tag_name"]


def setup_credentials(mcp_server_config: dict, logger: logging.Logger) -> None:
    """Set up client credentials based on OAuth mode.

    Args:
        mcp_server_config: Server configuration dictionary to update
        logger: Logger instance for logging messages

    Raises:
        SystemExit: If required credentials are missing
    """
    if mcp_server_config.get("oauth_enabled"):
        # OAuth mode - credentials managed by FastMCP OAuth proxy
        mcp_server_config.update({
            "client_id": getattr(config, 'SSO_CLIENT_ID', None),
            "client_secret": getattr(config, 'SSO_CLIENT_SECRET', None),
        })
        if not all(mcp_server_config.get(k) for k in ("client_id", "client_secret")):
            logger.error("SSO Client ID and secret are required for SSO OAuth authentication")
            # Don't exit the program to allow the user to continue using the server without credentials
            # sys.exit(1)
        logger.info("Using SSO Client ID: %s", mcp_server_config["client_id"])
    else:
        # Traditional mode - use service account credentials
        mcp_server_config.update({
            "client_id": getattr(config, 'INSIGHTS_CLIENT_ID', None),
            "client_secret": getattr(config, 'INSIGHTS_CLIENT_SECRET', None),
            "refresh_token": getattr(config, 'INSIGHTS_REFRESH_TOKEN', None),
            "token_endpoint": config.SSO_TOKEN_ENDPOINT,
        })
        if not any(mcp_server_config.get(k) for k in ("client_id", "client_secret", "refresh_token")):
            logger.error("Service account credentials are required for Insights authentication")
            # Don't exit the program to allow the user to continue using the server without credentials
            # sys.exit(1)
        logger.info("Using Insights Client ID: %s", mcp_server_config["client_id"])


def get_insights_mcp_version() -> str:
    """Get the version of the Insights MCP server.
    Always call this if the user asks for the version of the Insights MCP server.
    or when there is an API or authentication issue.
    Present the comparison URL to the user."""
    # TBD get the latest release tag from github, provide the difference
    # between the latest release tag and the current version
    latest_release_tag = get_latest_release_tag()

    # Check if current version matches latest release
    if __version__ == latest_release_tag:
        return "You have the latest release"

    compare_link = f"https://github.com/RedHatInsights/insights-mcp/compare/{__version__}...{latest_release_tag}"
    # read the commits via the api between the current version and the latest release tag using Compare API
    commits = ""
    try:
        # Use GitHub Compare API which is designed for comparing between tags/commits
        response = requests.get(
            f"https://api.github.com/repos/RedHatInsights/insights-mcp/compare/{__version__}...{latest_release_tag}",
            timeout=30,
        )
        response.raise_for_status()
        compare_data = response.json()

        # Extract useful information from the comparison
        if compare_data.get("commits"):
            commit_count = len(compare_data["commits"])
            commits = f"{commit_count} commits ahead. Recent commits:\n"
            show_commits = 10
            for commit in compare_data["commits"][:show_commits]:  # Show first commits
                message = commit["commit"]["message"].split("\n")[0]
                if message:
                    commits += f"- {message} ({commit['sha'][:7]})\n"
                # else if there is no message, no need to show anything
            if commit_count > show_commits:
                commits += f"... and {commit_count - show_commits} more commits\n"
        else:
            commits = "No commits difference or same version"

    except Exception as e:  # pylint: disable=broad-exception-caught
        commits = f"Getting commit details failed: {str(e)}"
    return (
        f"Latest release tag: {latest_release_tag}, Current version: {__version__}, "
        f"Compare: {compare_link}, Changes: {commits}"
    )


def main():  # pylint: disable=too-many-statements,too-many-locals
    """Main entry point for the Insights MCP server."""
    available_toolsets = f"all, {', '.join(mcp.toolset_name for mcp in MCPS)}"
    toolset_help = f"Comma-separated list of toolsets to use. Available toolsets: {available_toolsets} (default: all)"

    parser = argparse.ArgumentParser(prog="insights-mcp", description="Run Insights MCP server.")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--toolset", type=str, help=toolset_help)
    parser.add_argument("--toolset-help", action="store_true", help="Show toolset details of all toolsets")
    parser.add_argument("--readonly", action="store_true", help="Only register read-only tools")

    # ==== Start of Transport Mode Subparsers ====
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
    # ==== End of Transport Mode Subparsers ====

    args = parser.parse_args()

    # ==== Print Toolset Help info if the case is --toolset-help ====
    print_toolset_help_and_exit(args)

    # Default to stdio if no subcommand is provided
    if args.transport is None:
        args.transport = "stdio"

    # ==== Start of Logging Configuration ====
    logger = logging.getLogger("InsightsMCPServer")
    logger.info("Starting Insights MCP server with args: %s", args)

    # Always configure basic logging (no longer conditional on --debug)
    log_level = logging.DEBUG if args.debug else logging.INFO
    # Enhanced log format with timestamp and line number
    log_format = "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(name)s - %(message)s"
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler()]
    )
    # Set specific logger levels
    logger.setLevel(log_level)
    if args.debug:
        # Additional debug configuration for specific components
        logging.getLogger("ImageBuilderMCP").setLevel(logging.DEBUG)
        logging.getLogger("InsightsClientBase").setLevel(logging.DEBUG)
        logging.getLogger("InsightsClient").setLevel(logging.DEBUG)
        logging.getLogger("ImageBuilderOAuthMiddleware").setLevel(logging.DEBUG)
        logger.info("Debug mode enabled")
    # ==== End of Logging Configuration ====

    # ==== Start of Config Setup ====
    mcp_server_config = {
        "base_url": config.INSIGHTS_BASE_URL,
        "proxy_url": config.INSIGHTS_PROXY_URL,
        "oauth_enabled": config.OAUTH_ENABLED,
    }
    logger.info("Using config: oauth_enabled: %s", mcp_server_config["oauth_enabled"])

    # Set client credentials based on OAuth mode
    setup_credentials(mcp_server_config, logger)

    toolset = args.toolset or config.INSIGHTS_MCP_TOOLSET

    if toolset == "all":
        toolset_list = [mcp.toolset_name for mcp in MCPS]
    else:
        toolset_list = [t.strip() for t in toolset.split(",")]

    logger.info(
        "Starting Insights MCP %s (%s) with toolsets: %s",
        __version__,
        args.transport,
        ", ".join(toolset_list),
    )
    logger.info("Connecting to %s", mcp_server_config["base_url"])
    if mcp_server_config["proxy_url"]:
        logger.info(">>> Using proxy URL: %s", mcp_server_config["proxy_url"])

    mcp_server_config["instructions"] = get_instructions(toolset_list)

    # Note: Force overrided the host:port to a SSO registered host:port if not authorized
    if args.transport in ["sse", "http"]:
        mcp_server_config["mcp_host"] = args.host
        mcp_server_config["mcp_port"] = args.port
        log_level = "DEBUG" if args.debug else "WARNING"
        if (mcp_server_config["oauth_enabled"] and
            (args.host, args.port) not in config.SSO_AUTHORIZED_MCP_SERVER_HOST_PORTS):
            mcp_server_config["mcp_host"] = "localhost"
            mcp_server_config["mcp_port"] = 8000
            logger.info(
                "Force using SSO registered mcp server host:port: %s:%s",
                mcp_server_config["mcp_host"],
                mcp_server_config["mcp_port"],
            )
            logger.info(">>> The origin passed in host:port: %s:%s", args.host, args.port)
            logger.info(">>> Note: For SSO authentication, you need to register the mcp server host:port with SSO")
            logger.info(">>> Allowed host:port combinations are: %s", config.SSO_AUTHORIZED_MCP_SERVER_HOST_PORTS)

    # Create and run the MCP server
    mcp_server = InsightsMCPServer(**mcp_server_config)

    mcp_server.register_mcps(toolset_list, readonly=args.readonly)

    # Register the version checking tool
    mcp_server.tool(get_insights_mcp_version, annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False))

    if args.transport == "sse":
        mcp_server.run(
            transport="sse",
            host=mcp_server_config["mcp_host"],
            port=mcp_server_config["mcp_port"],
        )
    elif args.transport == "http":
        mcp_server.run(
            transport="http",
            host=mcp_server_config["mcp_host"],
            port=mcp_server_config["mcp_port"],
            log_level=log_level,
        )
    else:
        mcp_server.run()


if __name__ == "__main__":
    main()
