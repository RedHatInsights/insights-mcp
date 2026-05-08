# DeepEval upstream alignment

Target: [confident-ai/deepeval](https://github.com/confident-ai/deepeval)

## Candidates to contribute upstream

1. **Evaluation parameter names** — Stable resolution of `SingleTurnParams` vs legacy
   `LLMTestCaseParams` (see `compat.py`).
2. **OpenAI-compatible judging models** — Patterns for custom base URLs and Bearer
   authentication for `DeepEvalBaseLLM` (see `models.py` and `http_llm.py`).

## Workflow

1. Reproduce on a minimal Deepeval-only script outside this repository.
2. Open a GitHub issue with version pins and trace.
3. Prefer removing local shims once upstream ships an equivalent API.
