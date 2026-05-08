"""Exceptions for DeepEval support helpers shared with HTTP LLM callers."""


class MCPError(Exception):
    """Raised when an OpenAI-compat chat-completions request fails or returns an unexpected shape."""


__all__ = ["MCPError"]
