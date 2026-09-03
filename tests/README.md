# Testing Documentation

This directory contains shared tests and the reusable LLM evaluation harness for all MCP toolsets.
LLM tests use OpenAI-compatible model endpoints, including vLLM and gateway-hosted models.

## Test Structure

- `test_auth.py` - Authentication and OAuth tests
- `utils.py` - Shared testing utilities and helper functions
- `mcp_llm_eval/` - Reusable LLM test harness:
  - `README.md` - Authoritative documentation for the harness API, execution, and consumer fixtures
  - `llama_index_support/` - MCP agent wrapper; see `UPSTREAM.md`
  - `deepeval_support/` - DeepEval adapters and tool-call tracing; see `UPSTREAM.md`
  - `generators.py` - `create_test_suite()` for generated per-toolset tests
  - `llm_prompt_support.py` - Scenario resolution, execution, and assertions
  - `fixtures.py` - Shared agent, guardian, and logging fixtures
- `conftest.py` - Project-specific fixtures, collection-time credential skips, and the Python/DeepEval compatibility patch
- `../instrumentation_tests/` - Structural MCP checks (run ``make test-instrumentation``)
- `test_tokens.py` - MCP tool input token budget checks (see below)
- `llm_api_discovery.py` - Resolves `{cve_id}`, `{host_id}`, etc. from live Insights APIs before each test
- `src/<toolset>_mcp/tests/test_<toolset>_llm_prompts.py` - Generated per-toolset LLM tests

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

3. **Configure Insights credentials** for tests that start a real Insights MCP server. Set
   `INSIGHTS_CLIENT_ID` and `INSIGHTS_CLIENT_SECRET`, or the equivalent `LIGHTSPEED_*` variables.
   Without these credentials, project LLM tests are marked skipped during collection before server
   fixtures are started.

### Running Tests

```bash
make test

make test-instrumentation

# or
make test-verbose

# or
make test-very-verbose

# LLM integration tests only (requires test_config.json and Insights credentials)
make test-llm
# equivalent:
# env DEEPEVAL_TELEMETRY_OPT_OUT=YES uv run pytest -m llm -v

# One toolset only
uv run pytest src/vulnerability_mcp/tests/test_vulnerability_llm_prompts.py -m llm -v -rs
```

Each prompt registry in `src/<toolset>_mcp/test_prompts.py` declares `TestScenario` entries with
per-turn `expected_tools`, optional forbidden tools, argument expectations, and guardian criteria.
The generated suite fails if a turn calls none of its expected tools. Placeholders (`{cve_id}`, …)
are resolved from live APIs; scenarios skip when data is missing (`-rs`). Optional:
`INSIGHTS_TEST_WORKSPACE` for advisor workspace prompts. Regenerate example Markdown with
`make test-prompts-md`.

### LLM test tracing

When pytest collects any test parametrized with ``llm_config``, the shared fixture calls
``mcp_llm_eval.llm_tracing.enable_llm_test_tracing()`` once per session. That registers DeepEval
``instrument_llama_index`` on LlamaIndex's dispatcher (span fallback for tool asserts).
Actual ``tools_called`` for ``ToolCorrectnessMetric`` come from workflow stream events in
``mcp_llm_eval.deepeval_support.tracing``, not from Phoenix.

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
