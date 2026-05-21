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

`agent_mcp.py` is a **test harness** only (MCP discovery, `OpenAILike` matrix, multi-turn
`execute_with_reasoning`)—no Red Hat MCP domain assertions.

### Tool-call recording (native instrumentation)

Tool calls for DeepEval `ToolCorrectnessMetric` are **not** monkey-patched on MCP tools.
Instead:

1. **Workflow stream events** — `WorkflowToolCallCollector` records LlamaIndex workflow
   `ToolCall` events from `handler.stream_events()` (see `deepeval_support/tracing.py`).
2. **DeepEval** — `instrument_llama_index(get_dispatcher())` is enabled for LLM tests via
   `tests/llm_tracing.py` / session autouse in `tests/conftest.py` (span fallback only).

Dev dependency: `llama-index-llms-openai-like`. `MCPAgentWrapper` uses `OpenAILike` against
OpenAI-compatible remote endpoints (`MODEL_API` / `MODEL_ID` from test config).
`FunctionAgent.allow_parallel_tool_calls=False` is set on the agent (not via LLM
`additional_kwargs`, because some gateways reject `parallel_tool_calls` on the request).

### Gateway workarounds (debt)

These exist until system prompts and model behavior are stable across the LLM matrix:

| Workaround | Trigger | Goal |
|------------|---------|------|
| `_embed_chat_history_in_user_message` | `pro` in `model_id` (Gemini Pro) | Avoid multi-turn chat replay failures with tools |
| `_compact_chat_history_for_followup` | Any follow-up with `chat_history` | Strip tool messages that break strict gateways |
| Empty-response retry | No text and no tool calls after `agent.run` | Recover from occasional blank completions |

Remove each row when matrix runs no longer need it; track per-model failures in LLM test logs.
