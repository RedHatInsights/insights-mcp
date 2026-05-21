# Testing Documentation

This directory contains test suites for the Image Builder MCP server.
For now this is intended to be used with vLLM test agents.

## Test Structure

- `test_auth.py` - Authentication and OAuth tests
- `utils.py` - Shared testing utilities and helper functions
- `llama_index_support/` - LlamaIndex MCP agent (`MCPAgentWrapper`); see ``UPSTREAM.md`` there
- `deepeval_support/` - DeepEval adapters (tool-call tracing, OpenAI-compat judge models)
- `llm_tracing.py` - Session hook that enables DeepEval ``instrument_llama_index`` for ``@pytest.mark.llm`` tests
- `../instrumentation_tests/` - Structural MCP checks (run ``make test-instrumentation``)
- `conftest.py` - Pytest fixtures and configuration
- `test_tokens.py` - MCP tool input token budget checks (see below)

Image Builder specific tests are located in `src/image_builder_mcp/tests/`:
- `test_get_blueprints.py` - Blueprint retrieval tests
- `test_llm_integration_easy.py` - Basic LLM integration tests using deepeval
- `test_llm_integration_hard.py` - Advanced LLM integration tests using deepeval

## LLM Integration Testing

The LLM integration tests support matrix testing across multiple LLM configurations using deepeval framework.

### Setup

1. **Copy the example configuration:**
   ```bash
   cp test_config.json.example test_config.json
   ```

2. **Configure your models** by editing `test_config.json` with your API credentials:
   ```json
   {
     "llm_configurations": [
       {
         "name": "Primary Model",
         "MODEL_ID": "granite-3.1",
         "MODEL_API": "https://your-vLLM-server",
         "USER_KEY": "your-api-key"
       }
     ],
     "guardian_llm": {
       "name": "Optional model for Test evaluation",
       "MODEL_ID": "granite-3.2",
       "MODEL_API": "https://your-vLLM-server2",
       "USER_KEY": "your-api-key"
     }
   }
   ```

### Running Tests

```bash
make test

make test-instrumentation

# or
make test-verbose

# or
make test-very-verbose

# LLM integration tests only (requires test_config.json and Insights credentials)
uv run pytest -m llm -v
```

### LLM test tracing

When pytest collects any test parametrized with ``llm_config``, ``tests/conftest.py`` calls
``tests/llm_tracing.enable_llm_test_tracing()`` once per session. That registers DeepEval
``instrument_llama_index`` on LlamaIndex's dispatcher (span fallback for tool asserts).
Actual ``tools_called`` for ``ToolCorrectnessMetric`` come from workflow stream events in
``tests/deepeval_support/tracing.py``, not from Phoenix.

Environment:

- ``DEEPEVAL_TELEMETRY_OPT_OUT=YES`` — disable DeepEval telemetry (recommended in CI/docs).

### Fallback

If `test_config.json` is missing, tests fall back to environment variables: `MODEL_API`, `MODEL_ID`, `USER_KEY`.

## Tool input token tests

`test_tokens.py` checks that the full `--all-tools` catalog fits within an input token budget for each
entry in `llm_configurations` (not `guardian_llm`). Counts use the same OpenAI-style tool JSON as
`FunctionAgent` / `achat_with_tools`, tokenized with tiktoken.

Optional per-model override in `test_config.json`:

- `TIKTOKEN_ENCODING` — tiktoken encoding name (e.g. `cl100k_base`). Omit to use `encoding_for_model(MODEL_ID)` or fall back to `cl100k_base` with a warning for unknown models (e.g. Gemini).

Environment:

- `INSIGHTS_MCP_MAX_TOOL_INPUT_TOKENS` — maximum allowed tokens for the all-tools row (default: `15000`).

Generate the markdown overview (all toolsets + each toolset, all with `--all-tools`):

```bash
make docs/tool-tokens.md
# or
make generate-docs
uv run python scripts/dump_tool_tokens.py -o docs/tool-tokens.md
```

Run only the token tests:

```bash
uv run pytest tests/test_tokens.py -v
```

### Future Work

Implement single test using all three transports.
Use either HTTP-Streaming or stdio for all others. So test all transports with a simple test
and then choose one for all other LLM tests.
