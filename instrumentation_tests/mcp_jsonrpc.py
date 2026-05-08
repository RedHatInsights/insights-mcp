"""Minimal MCP JSON-RPC helpers for tests and instrumentation (no LlamaIndex)."""

import json
from typing import Any, Dict

# Used by MCP HTTP transport (JSON-RPC and SSE payloads).
DEFAULT_JSON_HEADERS = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}

__all__ = ["DEFAULT_JSON_HEADERS", "create_mcp_init_request", "parse_mcp_response"]


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
