"""Helpers for MCP tool descriptions exposed to function-calling LLMs.

MCP sends the full ``tool.description`` string to the model (including newlines).
Some gateways struggle with very long *aggregate* tool catalogs; optional patterns:

- **Full docstring** as ``description`` (see ``planning_mcp``).
- **Short title** via ``mcp_tool_title_from_docstring`` for UI/listing only.
- **Resources** (future): keep ``description`` short and point at
  ``read_resource`` for extended guidance (requires server resources + agent
  ``include_resources=True``).
"""


def mcp_tool_title_from_docstring(doc: str) -> str:
    """Return the first line of a tool docstring for tool title / summary."""
    return doc.strip().split("\n", 1)[0].strip()
