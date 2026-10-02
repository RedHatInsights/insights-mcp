# Instrumentation tests

These checks validate **structure and wiring** (tool catalogs, MCP contracts) without asserting LLM judgments or golden conversational behavior.

Run:

```bash
make test-instrumentation
```

The default ``make test`` / ``pytest tests`` flow **does not** collect this directory, so instrumentation failures are surfaced only when explicitly requested or in a dedicated CI step.
