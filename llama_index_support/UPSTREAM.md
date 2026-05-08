# LlamaIndex upstream alignment

Targets:

- [`run-llama/llama_index`](https://github.com/run-llama/llama_index) (`llama-index-core`, `llama-index-tools-mcp`)

## Defensive MCP schema patch

`non_iterable_bool_patch.py` works around `_resolve_field_type` assuming dict-shaped
schemas when `additionalProperties` can be JSON Schema boolean shorthand.

Prefer removing the patch once the root cause is fixed in `tool_spec_mixins`.

## MCP + Llama agents in tests

`agent_mcp.py` holds **LlamaIndex** `FunctionAgent` wiring plus MCP discovery used by behavioral
integration tests—no Red Hat MCP domain assertions.
