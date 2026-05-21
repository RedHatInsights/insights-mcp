# DeepEval upstream alignment

Target: [confident-ai/deepeval](https://github.com/confident-ai/deepeval)

## Behavioral test guardian LLM

Guardian/judge metrics in LLM integration tests use `deepeval.models.GPTModel` with
`MODEL_API`, `MODEL_ID`, and `USER_KEY` from test config (OpenAI-compatible remote
endpoints). Pass the same model to `GEval` and `ToolCorrectnessMetric` so deepeval does
not fall back to an unconfigured default `GPTModel`.

## LlamaIndex tool-call tracing

LLM tests call `instrument_llama_index(get_dispatcher())` from `tests/llm_tracing.py`.
`deepeval_support/tracing.py` maps workflow stream events and `AgentOutput` to
`deepeval.test_case.ToolCall` for `ToolCorrectnessMetric` (see `llama_index_support/UPSTREAM.md`).

## Candidates to contribute upstream

1. **Evaluation parameter names** — Stable resolution of `SingleTurnParams` vs legacy
   `LLMTestCaseParams` (see `compat.py`).

## Workflow

1. Reproduce on a minimal Deepeval-only script outside this repository.
2. Open a GitHub issue with version pins and trace.
3. Prefer removing local shims once upstream ships an equivalent API.
