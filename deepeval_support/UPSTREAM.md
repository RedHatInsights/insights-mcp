# DeepEval upstream alignment

Target: [confident-ai/deepeval](https://github.com/confident-ai/deepeval)

## Behavioral test guardian LLM

Guardian/judge metrics in LLM integration tests use `deepeval.models.GPTModel` with
`MODEL_API`, `MODEL_ID`, and `USER_KEY` from test config (OpenAI-compatible remote
endpoints). Pass the same model to `GEval` and `ToolCorrectnessMetric` so deepeval does
not fall back to an unconfigured default `GPTModel`.

## Candidates to contribute upstream

1. **Evaluation parameter names** — Stable resolution of `SingleTurnParams` vs legacy
   `LLMTestCaseParams` (see `compat.py`).

## Workflow

1. Reproduce on a minimal Deepeval-only script outside this repository.
2. Open a GitHub issue with version pins and trace.
3. Prefer removing local shims once upstream ships an equivalent API.
