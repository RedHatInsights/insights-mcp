"""Minimal MCP JSON-RPC helpers for tests and instrumentation (no LlamaIndex)."""

import json
from typing import Any, Dict, List, Optional

import requests

# Used by MCP HTTP transport (JSON-RPC and SSE payloads).
DEFAULT_JSON_HEADERS = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}

__all__ = [
    "DEFAULT_JSON_HEADERS",
    "create_mcp_init_request",
    "fetch_mcp_instructions_http",
    "fetch_mcp_instructions_stdio",
    "parse_mcp_response",
]


def parse_mcp_response(response_text: str) -> Dict[str, Any]:
    """Parse MCP response which could be JSON or SSE format."""
    try:
        return json.loads(response_text)
    except json.JSONDecodeError as exc:
        for line in response_text.split("\n"):
            if line.startswith("data: "):
                data_part = line[6:]
                try:
                    return json.loads(data_part)
                except json.JSONDecodeError:
                    continue
        raise ValueError(f"No valid JSON found in response: {response_text}") from exc


def create_mcp_init_request() -> dict:
    """Create standard MCP initialization request."""
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"},
        },
    }


def fetch_mcp_instructions_http(
    server_url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 10,
) -> str:
    """Return MCP ``initialize`` ``instructions`` from an HTTP or SSE MCP endpoint."""
    request_headers = dict(DEFAULT_JSON_HEADERS)
    if headers:
        request_headers.update(headers)
    response = requests.post(
        server_url,
        json=create_mcp_init_request(),
        headers=request_headers,
        timeout=timeout,
    )
    if response.status_code != 200:
        return ""
    response_data = parse_mcp_response(response.text)
    if not isinstance(response_data, dict):
        return ""
    result = response_data.get("result")
    if not isinstance(result, dict):
        return ""
    instructions = result.get("instructions", "")
    return instructions if isinstance(instructions, str) else ""


async def fetch_mcp_instructions_stdio(command: str, args: List[str]) -> str:
    """Return MCP ``initialize`` ``instructions`` from a stdio MCP server subprocess."""
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    server_parameters = StdioServerParameters(command=command, args=args)
    async with stdio_client(server_parameters) as (read, write):
        async with ClientSession(read, write) as session:
            init_result = await session.initialize()
            return init_result.instructions or ""
