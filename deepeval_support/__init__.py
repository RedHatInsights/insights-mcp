"""Shims and adapters for DeepEval aimed at upstream contributions.

Domain-specific eval scenarios stay under ``tests/`` and ``src/**/tests/``.
"""

from deepeval_support.compat import EvalCaseParams
from deepeval_support.tool_calls import tool_call_record

__all__ = ["EvalCaseParams", "tool_call_record"]
