"""Test command line arguments for the Insights MCP server.

This module tests the --toolset command line argument to ensure that the correct
set of tools is available based on the toolset configuration.
"""

import asyncio
from typing import Any, Dict, List, Set

import pytest
from llama_index.tools.mcp import BasicMCPClient, McpToolSpec

from tests.utils import cleanup_server_process, start_insights_mcp_server


def get_mcp_tools_with_toolset(transport: str, toolset: str | None = None, readonly: bool = False) -> List[Any]:
    """Get MCP tools for a specific transport and toolset configuration.

    Args:
        transport: Transport type ('http', 'sse', or 'stdio')
        toolset: Toolset to use (e.g., 'all', 'image-builder', 'inventory')
        readonly: If True, only register read-only tools

    Returns:
        List of MCP tools
    """
    server_url, server_process = start_insights_mcp_server(transport, toolset=toolset, readonly=readonly)

    try:
        if server_url == "stdio":
            # For stdio, use subprocess approach with toolset
            args = ["-m", "insights_mcp.server"]
            if toolset is not None:
                args.extend(["--toolset", toolset])
            if not readonly:
                args.append("--all-tools")
            args.append("stdio")
            client = BasicMCPClient("python", args=args)
        else:
            # For HTTP/SSE, connect to running server
            client = BasicMCPClient(server_url)

        tool_spec = McpToolSpec(client=client)

        async def _fetch():
            return await tool_spec.to_tool_list_async()

        return asyncio.run(_fetch())

    finally:
        cleanup_server_process(server_process)


class TestCliArguments:
    """Test class for command line argument functionality."""

    # Expected tools for each toolset
    EXPECTED_TOOLS: Dict[str, Set[str]] = {
        "insights-mcp": {
            "get_mcp_version",
        },
        "image-builder": {
            "image-builder__get_openapi",
            "image-builder__create_blueprint",
            "image-builder__update_blueprint",
            "image-builder__get_blueprints",
            "image-builder__get_blueprint_details",
            "image-builder__get_composes",
            "image-builder__get_compose_details",
            "image-builder__blueprint_compose",
            "image-builder__get_distributions",
        },
        "inventory": {
            "inventory__list_hosts",
            "inventory__get_host_details",
            "inventory__get_host_system_profile",
            "inventory__get_host_tags",
        },
        "vulnerability": {
            "vulnerability__get_openapi",
            "vulnerability__get_cves",
        },
        "remediations": {
            "remediations__create_vulnerability_playbook",
        },
        "advisor": {
            "advisor__get_active_rules",
            "advisor__get_rule_from_node_id",
            "advisor__get_rule_details",
            "advisor__get_hosts_hitting_a_rule",
            "advisor__get_hosts_details_for_rule",
            "advisor__get_rule_by_text_search",
            "advisor__get_recommendations_stats",
        },
    }

    @pytest.mark.parametrize("transport", ["stdio"])
    def test_default_toolset_includes_all_tools(self, transport: str):
        """Test that when --toolset is not specified, all tools are available."""
        # Test with no toolset specified (should default to "all")
        tools = get_mcp_tools_with_toolset(transport, toolset=None)
        tool_names = {getattr(t.metadata, "name", "") for t in tools}

        # Should include tools from all toolsets
        all_expected_tools = set()
        for toolset_tools in self.EXPECTED_TOOLS.values():
            all_expected_tools.update(toolset_tools)

        # Check that we have tools from multiple toolsets
        has_image_builder = any(name.startswith("image-builder__") for name in tool_names)
        has_inventory = any(name.startswith("inventory__") for name in tool_names)

        assert has_image_builder, f"Expected image-builder tools. Available: {tool_names}"
        assert has_inventory, f"Expected inventory tools. Available: {tool_names}"

        # Verify specific core tools are present
        expected_core_tools = {
            "image-builder__get_blueprints",
            "inventory__list_hosts",
        }
        missing_tools = expected_core_tools - tool_names
        assert not missing_tools, f"Missing expected tools: {missing_tools}. Available: {tool_names}"

    @pytest.mark.parametrize("transport", ["stdio"])
    def test_image_builder_toolset_only(self, transport: str):
        """Test that when --toolset=image-builder, only image-builder tools are available."""
        tools = get_mcp_tools_with_toolset(transport, toolset="image-builder")
        tool_names = {getattr(t.metadata, "name", "") for t in tools}

        # Should only have image-builder tools
        image_builder_tools = {name for name in tool_names if name.startswith("image-builder__")}
        non_image_builder_tools = {name for name in tool_names if not name.startswith("image-builder__")}
        # also remove insights-mcp tools from non_image_builder_tools
        non_image_builder_tools = {
            name for name in non_image_builder_tools if name not in self.EXPECTED_TOOLS["insights-mcp"]
        }

        assert image_builder_tools, f"Expected image-builder tools. Available: {tool_names}"
        assert not non_image_builder_tools, f"Expected only image-builder tools, but found: {non_image_builder_tools}"

        # Verify specific image-builder tools are present
        expected_tools = {"image-builder__get_blueprints", "image-builder__get_composes"}
        # insights-mcp tools are always available
        expected_tools.update(self.EXPECTED_TOOLS["insights-mcp"])
        missing_tools = expected_tools - tool_names
        assert not missing_tools, f"Missing expected image-builder tools: {missing_tools}"

    @pytest.mark.parametrize("transport", ["stdio"])
    def test_inventory_toolset_only(self, transport: str):
        """Test that when --toolset=inventory, only inventory tools are available."""
        tools = get_mcp_tools_with_toolset(transport, toolset="inventory")
        tool_names = {getattr(t.metadata, "name", "") for t in tools}

        # Should only have inventory tools
        inventory_tools = {name for name in tool_names if name.startswith("inventory__")}
        non_inventory_tools = {name for name in tool_names if not name.startswith("inventory__")}
        # also remove insights-mcp tools from non_inventory_tools
        non_inventory_tools = {name for name in non_inventory_tools if name not in self.EXPECTED_TOOLS["insights-mcp"]}

        assert inventory_tools, f"Expected inventory tools. Available: {tool_names}"
        assert not non_inventory_tools, f"Expected only inventory tools, but found: {non_inventory_tools}"

        # Verify specific inventory tools are present
        expected_tools = {"inventory__list_hosts", "inventory__get_host_details"}
        # insights-mcp tools are always available
        expected_tools.update(self.EXPECTED_TOOLS["insights-mcp"])
        missing_tools = expected_tools - tool_names
        assert not missing_tools, f"Missing expected inventory tools: {missing_tools}"

    @pytest.mark.parametrize("transport", ["stdio"])
    def test_combined_toolsets(self, transport: str):
        """Test that when --toolset=image-builder,inventory, both toolsets are available."""
        tools = get_mcp_tools_with_toolset(transport, toolset="image-builder, inventory")
        tool_names = {getattr(t.metadata, "name", "") for t in tools}

        # Should have both image-builder and inventory tools
        image_builder_tools = {name for name in tool_names if name.startswith("image-builder__")}
        inventory_tools = {name for name in tool_names if name.startswith("inventory__")}
        other_tools = {
            name for name in tool_names if not name.startswith("image-builder__") and not name.startswith("inventory__")
        }
        # also remove insights-mcp tools from other_tools
        other_tools = {name for name in other_tools if name not in self.EXPECTED_TOOLS["insights-mcp"]}

        assert image_builder_tools, f"Expected image-builder tools. Available: {tool_names}"
        assert inventory_tools, f"Expected inventory tools. Available: {tool_names}"
        assert not other_tools, f"Expected only image-builder and inventory tools, but found: {other_tools}"

        # Verify specific tools from both toolsets are present
        expected_tools = {
            "image-builder__get_blueprints",
            "inventory__list_hosts",
        }
        # insights-mcp tools are always available
        expected_tools.update(self.EXPECTED_TOOLS["insights-mcp"])
        missing_tools = expected_tools - tool_names
        assert not missing_tools, f"Missing expected tools: {missing_tools}"

    @pytest.mark.parametrize("transport", ["stdio"])
    def test_explicit_all_toolset(self, transport: str):
        """Test that when --toolset=all, all tools are available (same as default)."""
        tools_default = get_mcp_tools_with_toolset(transport, toolset=None)
        tools_explicit_all = get_mcp_tools_with_toolset(transport, toolset="all")

        tool_names_default = {getattr(t.metadata, "name", "") for t in tools_default}
        tool_names_explicit_all = {getattr(t.metadata, "name", "") for t in tools_explicit_all}

        # Both should have the same tools
        assert tool_names_default == tool_names_explicit_all, (
            f"Default toolset and explicit 'all' should have same tools. "
            f"Default: {tool_names_default}, Explicit all: {tool_names_explicit_all}"
        )

    @pytest.mark.parametrize("transport", ["stdio"])
    def test_readonly_flag_filters_tools(self, transport: str):
        """Test that --readonly flag filters out non-readonly tools."""
        # Get some toolsets with readonly flag to test
        tools = get_mcp_tools_with_toolset(transport, toolset="image-builder,vulnerability,remediations", readonly=True)
        tool_names = {getattr(t.metadata, "name", "") for t in tools}

        # Readonly tools that should be present
        readonly_tools = {
            "image-builder__get_openapi",
            "image-builder__get_blueprints",
            "image-builder__get_blueprint_details",
            "image-builder__get_composes",
            "image-builder__get_compose_details",
            "image-builder__get_distributions",
            "vulnerability__get_openapi",
            "vulnerability__get_cves",
            "vulnerability__get_cve",
            "vulnerability__get_cve_systems",
            "vulnerability__get_system_cves",
            "vulnerability__get_systems",
            "vulnerability__explain_cves",
        }

        # Non-readonly tools that should NOT be present
        non_readonly_tools = {
            "image-builder__create_blueprint",
            "image-builder__update_blueprint",
            "image-builder__blueprint_compose",
            "remediations__create_vulnerability_playbook",
        }

        # insights-mcp tools are always available
        readonly_tools.update(self.EXPECTED_TOOLS["insights-mcp"])

        # Check that all readonly tools are present
        missing_readonly = readonly_tools - tool_names
        assert not missing_readonly, f"Missing expected readonly tools: {missing_readonly}. Available: {tool_names}"

        # Check that non-readonly tools are NOT present
        unexpected_non_readonly = non_readonly_tools & tool_names
        assert not unexpected_non_readonly, (
            f"Found non-readonly tools that should be filtered: {unexpected_non_readonly}"
        )
