"""Register DeepEval LlamaIndex instrumentation for LLM integration tests.

Phoenix/OpenInference is not used here: tool-call recording for assertions comes from
workflow stream events (``tests.deepeval_support.tracing``) and optional DeepEval spans via
``instrument_llama_index``. This module exists so pytest can enable that hook once per
session when LLM matrix tests are collected (see ``tests/conftest.py``).
"""

from __future__ import annotations

import logging

_LOGGER = logging.getLogger(__name__)

_LLAMA_INDEX_INSTRUMENTED: bool = False


def enable_deepeval_llama_index_tracing() -> None:
    """Register DeepEval's LlamaIndex event handler once per process."""
    global _LLAMA_INDEX_INSTRUMENTED  # pylint: disable=global-statement
    if _LLAMA_INDEX_INSTRUMENTED:
        return
    import llama_index.core.instrumentation as instrument
    from deepeval.integrations.llama_index import instrument_llama_index

    instrument_llama_index(instrument.get_dispatcher())
    _LLAMA_INDEX_INSTRUMENTED = True
    _LOGGER.debug("DeepEval instrument_llama_index enabled")


def enable_llm_test_tracing() -> None:
    """Enable tracing used during LLM behavioral tests (DeepEval only)."""
    enable_deepeval_llama_index_tracing()


__all__ = ["enable_deepeval_llama_index_tracing", "enable_llm_test_tracing"]
