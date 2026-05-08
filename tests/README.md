# Testing Documentation

This directory contains test suites for the Image Builder MCP server.
For now this is intended to be used with vLLM test agents.

## Test Structure

- `test_auth.py` - Authentication and OAuth tests
- `utils.py` - Shared testing utilities and helper functions
- `../llama_index_support/` - LlamaIndex MCP agent (`MCPAgentWrapper`) and bool-schema patch — see ``UPSTREAM.md`` there
- `../deepeval_support/` - DeepEval adapters (e.g. OpenAI-compat judge models) — see ``UPSTREAM.md`` there
- `../instrumentation_tests/` - Structural MCP checks (run ``make test-instrumentation``)
- `conftest.py` - Pytest fixtures and configuration

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
```

### Fallback

If `test_config.json` is missing, tests fall back to environment variables: `MODEL_API`, `MODEL_ID`, `USER_KEY`.

### Future Work

Implement single test using all three transports.
Use either HTTP-Streaming or stdio for all others. So test all transports with a simple test
and then choose one for all other LLM tests.
