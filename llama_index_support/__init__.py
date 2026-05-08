"""LlamaIndex-oriented patches and MCP agent helpers."""

from llama_index_support.agent_mcp import MCPAgentWrapper
from llama_index_support.non_iterable_bool_patch import apply_llama_index_bool_patch

__all__ = ["MCPAgentWrapper", "apply_llama_index_bool_patch"]
