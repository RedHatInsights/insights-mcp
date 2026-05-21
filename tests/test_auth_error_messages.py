"""Tests for mounted-tools-aware authentication and RBAC error messages."""

import httpx
import pytest

from insights_mcp.client import (
    RBAC_DIAGNOSTIC_TOOL,
    InsightsOAuth2Client,
    build_mounted_tool_names,
)


@pytest.mark.parametrize(
    "mounted_tool_names,expect_rbac",
    [
        (build_mounted_tool_names(["image-builder"]), False),
        (build_mounted_tool_names(["image-builder", "rbac"]), True),
    ],
)
def test_no_auth_error_mentions_rbac_only_when_mounted(mounted_tool_names, expect_rbac):
    """no_auth_error should reference rbac diagnostics only when that tool is mounted."""
    client = InsightsOAuth2Client(
        client_id=None,
        client_secret=None,
        mcp_transport="http",
        token_endpoint="https://test.example.com/token",
        mounted_tool_names=mounted_tool_names,
    )
    error_msg = client.no_auth_error(ValueError("Missing credentials"))

    assert "get_mcp_version" in error_msg
    assert ("rbac__get_all_access" in error_msg) is expect_rbac
    assert "Don't proceed" not in error_msg


@pytest.mark.parametrize(
    "mounted_tool_names,expect_rbac",
    [
        (build_mounted_tool_names(["image-builder"]), False),
        (build_mounted_tool_names(["rbac"]), True),
    ],
)
def test_no_rbac_error_mentions_rbac_only_when_mounted(mounted_tool_names, expect_rbac):
    """no_rbac_error should reference rbac diagnostics only when that tool is mounted."""
    client = InsightsOAuth2Client(
        client_id="test-id",
        client_secret="test-secret",
        mcp_transport="http",
        token_endpoint="https://test.example.com/token",
        mounted_tool_names=mounted_tool_names,
    )
    response = httpx.Response(403, request=httpx.Request("GET", "https://example.com"))
    error = httpx.HTTPStatusError("Forbidden", request=response.request, response=response)
    error_msg = client.no_rbac_error(error)

    assert "get_mcp_version" in error_msg
    assert (RBAC_DIAGNOSTIC_TOOL in error_msg) is expect_rbac
    assert "Don't proceed" not in error_msg
