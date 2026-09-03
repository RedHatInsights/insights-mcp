# `mcp_llm_eval`

`mcp_llm_eval` is the reusable LLM-evaluation harness for MCP toolsets. It is
currently a test-only module under this repository's `tests/` directory.

This document describes the public scenario model, how scenarios are executed,
and the fixtures that a consuming project must provide.

## The scenario model

A registry contains named `TestScenario` objects. A `TestScenario` contains an
ordered tuple of `PromptWithTools` objects, one object for each user turn:

```text
TestScenarioRegistry
└── TestScenario (prompt_id: "get_host")
    ├── turns: tuple[PromptWithTools, ...]
    │   ├── PromptWithTools (turn 1)
    │   └── PromptWithTools (turn 2)
    ├── threshold
    ├── conversation_criteria
    └── assert_no_memory_overflow
```

One MCP agent is used for all turns in a scenario. This is important: later
turns see the conversation memory and tool results from earlier turns. The
generated pytest suite then parametrizes each complete scenario independently
for every configured model. For example, two model configurations produce two
test cases for every scenario.

### `PromptWithTools`

`PromptWithTools` describes one user prompt and the tool behavior expected in
that turn.

| Parameter | Type | Meaning |
| --- | --- | --- |
| `prompt` | `str` | Prompt template sent to the model. It may contain placeholders such as `{host_id}`; those are resolved from the consumer's `llm_api_context` fixture before execution. |
| `expected_tools` | `tuple[str, ...]` | Tool names checked for this turn. The direct assertion requires at least one call to one of these tools when the tuple is non-empty. All listed names are also passed to the guardian `ToolCorrectnessMetric`. |
| `forbidden_tools` | `tuple[str, ...]` | Tool names that must not be called during this turn. |
| `expected_args` | `dict[str, list[dict[str, Any]]] \| None` | Expected calls grouped by tool name. For each tool, the number and order of calls are checked. Each expected dictionary specifies a subset of the arguments, so additional model-generated arguments are allowed. Values are compared literally; placeholders are not substituted. Every key must also appear in `expected_tools`. |
| `turn_criteria` | `str \| None` | Optional single-turn natural-language criterion evaluated against that turn with DeepEval `GEval`. |

The expected tool names are the MCP names exposed to the agent, including any
toolset prefix used by the server. An individual turn may use an empty
`expected_tools` tuple, but this skips only the direct expected-tool assertion;
it does not assert that no tool is called. The guardian tool metric still runs
for that turn when `threshold > 0`, and the agent may still request a tool.
The scenario as a whole must declare at least one expected tool.

When multiple tools are listed, the direct assertion accepts any one of them,
but the guardian metric evaluates the complete list. Therefore, do not use
multiple names as guardian-metric alternatives unless that difference is
intentional. Set `threshold=0` when a turn's tools are alternatives and only
the direct assertion should apply.

Example:

```python
PromptWithTools(
    prompt="Show details for host {host_id}",
    expected_tools=("inventory__get_host",),
    forbidden_tools=("inventory__delete_host",),
    expected_args={
        "inventory__get_host": [{"host_id": "host-12345"}],
    },
    turn_criteria="The answer accurately summarizes the returned host.",
)
```

`expected_args` is intentionally keyed by tool name and contains a list so it
can express repeated calls:

```python
expected_args={
    "inventory__get_host": [
        {"host_id": "first-host"},
        {"host_id": "second-host"},
    ],
}
```

Only `prompt` is formatted from `llm_api_context`. Supply resolved, literal
argument values in `expected_args`, as in the `host-12345` example above.

The direct assertion checks calls to the same tool in their execution order.
It does not require unspecified arguments to be absent.

### `TestScenario`

`TestScenario` describes the complete multi-turn interaction.

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `turns` | `tuple[PromptWithTools, ...]` | required | Ordered user turns. The turns are executed with one agent and shared conversation memory. At least one turn is required. |
| `threshold` | `float` | `0.6` | Threshold passed to the guardian `ToolCorrectnessMetric`. It must be between `0` and `1`, inclusive. `0` disables this guardian metric only; direct tool and argument assertions still run. |
| `conversation_criteria` | `str \| None` | `None` | Optional criterion for the complete conversation. It is evaluated after all turns with a DeepEval `ConversationalTestCase` and `ConversationalGEval`. |
| `assert_no_memory_overflow` | `bool` | `False` | When true, checks after the scenario that the agent's active memory stays within its configured token limit. |

Construction validates that `turns` is not empty, that at least one turn has
`expected_tools`, and that `threshold` is in `[0, 1]`. An empty
`expected_tools` tuple on an individual turn is allowed, but it is not a
no-tool assertion. To avoid guardian tool scoring for such a scenario, set
`threshold=0`; direct expected-tool, forbidden-tool, and argument assertions
still run.

Use `turn_criteria` for a property of one model response. Use
`conversation_criteria` for behavior that depends on the complete sequence of
turns, such as whether the assistant uses context from an earlier request.

### `TestScenarioRegistry`

`TestScenarioRegistry` is the toolset-facing collection of scenarios. Define
it with keyword arguments; the keyword is the stable `prompt_id` used in pytest
IDs and log messages:

```python
from mcp_llm_eval.data import PromptWithTools, TestScenario, TestScenarioRegistry

PROMPTS = TestScenarioRegistry(
    list_hosts=TestScenario(
        turns=(
            PromptWithTools(
                prompt="List my hosts",
                expected_tools=("inventory__list_hosts",),
            ),
        ),
    ),
)
```

Parameters and behavior:

- `**entries: TestScenario` — named scenarios. At least one entry is required.
- Entry order is retained, so generated tests and generated markdown are
  deterministic.
- `iter_test_scenarios()` — converts the registry entries into the normalized
  records consumed by the generator. Prompt placeholders are substituted when
  the test runs; `expected_args` values are not substituted.

## Defining and generating a suite

Each toolset defines `PROMPTS` and creates a pytest class with the shared
generator:

```python
from mcp_llm_eval.data import PromptWithTools, TestScenario, TestScenarioRegistry
from mcp_llm_eval.generators import create_test_suite

PROMPTS = TestScenarioRegistry(
    list_hosts=TestScenario(
        turns=(
            PromptWithTools(
                prompt="List my hosts",
                expected_tools=("inventory__list_hosts",),
            ),
        ),
    ),
)

TestInventoryLLMPrompts = create_test_suite(PROMPTS, "TestInventoryLLMPrompts")
```

The generator creates one parametrized test for every pair of:

1. a scenario in the registry; and
2. an entry in `llm_configurations`.

Therefore every test scenario runs for every configured model. A guardian
model may be configured separately for evaluation, but it does not replace or
reduce the model matrix.

## Execution and assertions

For each scenario, the generated test performs these operations in order:

1. Resolve all prompt placeholders from `llm_api_context`. If required live
   data is unavailable, the scenario is skipped with a pytest reason.
2. Initialize one MCP agent for the selected model.
3. Execute every prompt turn in order, preserving conversation memory.
4. For each turn, directly assert expected tools when `expected_tools` is
   non-empty, forbidden tools, and expected arguments.
5. For each turn, evaluate `turn_criteria`, if present, as a
   single-turn criterion, and evaluate guardian tool correctness when
   `threshold > 0`.
6. Evaluate `conversation_criteria`, if present, against the full alternating
   user/assistant conversation after all turns.
7. Check memory overflow when `assert_no_memory_overflow` is true.

Direct assertions retain the complete tool-call sequence. The direct
`expected_tools` assertion treats its names as alternatives, requiring one of
them to be called. The guardian `ToolCorrectnessMetric` receives every listed
name as an expected tool, so a tuple containing multiple alternatives can
score differently from the direct assertion. Set `threshold=0` to disable
guardian tool scoring when that distinction matters. This distinction is
intentional: `expected_tools` is not an alternatives list for guardian
scoring. The
`ToolCorrectnessMetric` adapter has a narrower compatibility rule: it passes at
most one call per tool name, keeping the first call in deterministic
first-seen order because that metric expects unique tool names. This does not
change the direct assertions or the conversation evaluation.

The data helpers also provide:

- `format_template_for_markdown(template, placeholder_examples)` — render a
  prompt with documentation-only placeholder values.
- `collect_markdown_prompts(registry, placeholder_examples)` — collect
  deduplicated prompt examples in registry and turn order for
  `make test-prompts-md`.

## Fixtures supplied by the consumer

The consuming project registers the generic fixtures from its pytest
configuration:

```python
pytest_plugins = ("mcp_llm_eval.fixtures",)
```

It must provide these fixtures:

### Required fixtures

- `mcp_server_url` — the URL of a running HTTP/SSE MCP server, or the literal
  value `"stdio"` to launch an MCP server process through the configured stdio
  command. For HTTP/SSE, the consumer starts and stops the server and decides
  which toolset it exposes. For stdio, the consumer supplies
  `mcp_stdio_config`.
- `llm_api_context` — normally a session-scoped `dict[str, str]` containing
  values for placeholders used by scenarios, such as `cve_id` or `host_id`.
  The consumer obtains these values from its live APIs.

### Optional overrides

The harness supplies defaults, but the consumer may override them:

- `mcp_http_headers: dict[str, str] | None` — headers used when connecting to
  the MCP server over HTTP. The default is `None`.
- `mcp_stdio_config: tuple[str, list[str]]` — executable and argument list for
  stdio connections when `mcp_server_url` is `"stdio"`. The default is
  `("python", ["-m", "mcp_server", "stdio"])`.
- `mcp_memory_token_limit: int` — agent memory limit. The default is `16384`.
- `verbose_logger` — logging fixture if the consumer needs custom formatting
  or verbosity behavior.

The consumer also owns project-specific credential skips and the server
process lifecycle. The generic `test_agent` fixture reads the generated
test's `llm_config`, initializes an `MCPAgentWrapper`, and closes it even when
initialization fails part-way through. The generic `guardian_agent` uses the
configured `guardian_llm`, or the selected matrix model when no guardian is
configured.

## Model configuration and commands

The current repository loader looks for `test_config.json` at the repository
root. Start from `test_config.json.example`:

```json
{
  "llm_configurations": [
    {
      "name": "Primary Model",
      "MODEL_ID": "model-id",
      "MODEL_API": "https://model.example/v1",
      "USER_KEY": "your-api-key"
    }
  ],
  "guardian_llm": {
    "name": "Evaluation Model",
    "MODEL_ID": "guardian-id",
    "MODEL_API": "https://guardian.example/v1",
    "USER_KEY": "guardian-api-key"
  }
}
```

Each matrix entry needs `name`, `MODEL_ID`, `MODEL_API`, and `USER_KEY`.
Matrix entries may use exact `${ENV_VAR}` values, which are substituted from
the environment. If the file is absent or invalid, the loader falls back to
`MODEL_API`, `MODEL_ID`, and `USER_KEY` environment variables.

Run the matrix with:

```bash
make test-llm
# equivalent:
env DEEPEVAL_TELEMETRY_OPT_OUT=YES uv run pytest -m llm -v
```

Run one generated suite with:

```bash
uv run pytest src/vulnerability_mcp/tests/test_vulnerability_llm_prompts.py -m llm -v -rs
```

Use `-rs` to see skip reasons. These are live integration tests: they require
model access and, for toolsets that call Insights APIs, the relevant Insights
credentials. `make test-prompts-md` regenerates prompt-example markdown.
