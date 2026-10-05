# LlamaIndex upstream alignment

Targets:

- [`run-llama/llama_index`](https://github.com/run-llama/llama_index) (`llama-index-core`, `llama-index-tools-mcp`)

## MCP schema handling (bool `additionalProperties`)

LlamaIndex used to recurse into boolean `additionalProperties` and call
`_resolve_field_type` with a `bool`. Upstream addressed this in PR
[#20082](https://github.com/run-llama/llama_index/pull/20082) (shipped in
**llama-index-tools-mcp 0.4.2+**; this repo pins 0.4.8 in `uv.lock`).

## MCP + Llama agents in tests

`agent_mcp.py` is a **test harness** only (MCP discovery, `OpenAILike` matrix, multi-turn
`execute_with_reasoning`)—no Red Hat MCP domain assertions.

### Multi-turn chat history

Uses [`llama_index.core.memory.Memory`](https://developers.llamaindex.ai/python/framework/module_guides/deploying/agents/memory/):

- `Memory.from_defaults(session_id=..., token_limit=...)` per wrapper instance; the project supplies
  the limit through the `mcp_memory_token_limit` fixture (default 16384).
- `await memory.aset(prior_history)` before each turn
- `AgentWorkflowStartEvent(user_msg=..., memory=memory, max_iterations=...)` is passed
  to `agent.run(ctx=ctx, start_event=start_event)` (no gateway-specific history rewriting)
- `await memory.aget()` returned to tests for the next turn

If a remote model fails multi-turn replay (e.g. tool messages in history), fix prompts,
tests, or `Memory` token settings—do not reintroduce per-model string hacks in this harness.

### Tool-call recording (native instrumentation)

Tool calls for DeepEval `ToolCorrectnessMetric` are recorded from LlamaIndex workflow
`ToolCall` stream events (`tests/mcp_llm_eval/deepeval_support/tracing.py`). DeepEval
`instrument_llama_index` is enabled for LLM tests via `tests/mcp_llm_eval/llm_tracing.py`.

### MCP initialize instructions (test harness)

`McpToolSpec` does not attach MCP `initialize` `instructions` to tools. The harness loads
them via `mcp_llm_eval.mcp_jsonrpc` (HTTP/SSE POST or stdio `ClientSession`) and
prepends them to the **first user turn** of each conversation
(`format_user_message_with_mcp_instructions`). `FunctionAgent.system_prompt` stays `None`
so Granite and similar models keep a clean tool-calling template.

Dev dependency: `llama-index-llms-openai-like`. `MCPAgentWrapper` uses `OpenAILike` against
OpenAI-compatible remote endpoints (`MODEL_API` / `MODEL_ID` from test config).
`FunctionAgent.allow_parallel_tool_calls=False` is set on the agent (not via LLM
`additional_kwargs`, because some gateways reject `parallel_tool_calls` on the request).
