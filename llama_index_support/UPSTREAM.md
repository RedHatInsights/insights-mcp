# LlamaIndex upstream alignment

Targets:

- [`run-llama/llama_index`](https://github.com/run-llama/llama_index) (`llama-index-core`, `llama-index-tools-mcp`)

## MCP schema handling (historical bool `additionalProperties` crash)

LlamaIndex used to recurse into boolean `additionalProperties` and call
`_resolve_field_type` with a `bool`. Upstream addressed this for real schemas in PR
[#20082](https://github.com/run-llama/llama_index/pull/20082) (shipped in
**llama-index-tools-mcp 0.4.2**). `_resolve_field_type` itself still assumes dict-shaped
schemas; a small optional hardening would be an `isinstance(field_schema, bool)` guard
upstream if another call site ever passes bare booleans.

`non_iterable_bool_patch.py` only retains a deprecated no-op import check (`apply_llama_index_bool_patch`).

## MCP + Llama agents in tests

`agent_mcp.py` holds **LlamaIndex** `FunctionAgent` wiring plus MCP discovery used by behavioral
integration tests—no Red Hat MCP domain assertions.

Dev dependency: `llama-index-llms-openai-like`. `MCPAgentWrapper` uses `OpenAILike` against
OpenAI-compatible remote endpoints (`MODEL_API` / `MODEL_ID` from test config). Requests pass
`additional_kwargs={"parallel_tool_calls": False}` for behavioral tests.
