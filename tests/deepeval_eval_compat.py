"""DeepEval evaluation-parameter enum across deepeval 3.9.x pins.

Newer releases renamed ``LLMTestCaseParams`` to ``SingleTurnParams`` and only expose
the legacy name via ``__getattr__``, which pylint does not treat as an importable
symbol. Resolve at runtime without tripping static analysis on either layout.

This module lives under the top-level ``tests`` package (with ``tests.utils``) so
pytest importlib collection and ``pythonpath`` match pylint's ``tests/`` root.
"""

import importlib

_test_case_mod = importlib.import_module("deepeval.test_case")
EvalCaseParams = getattr(_test_case_mod, "SingleTurnParams", None) or getattr(_test_case_mod, "LLMTestCaseParams")

__all__ = ["EvalCaseParams"]
