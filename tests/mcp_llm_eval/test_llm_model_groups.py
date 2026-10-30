"""Unit tests for per-model LLM xdist grouping."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from tests.mcp_llm_eval.fixtures import assign_llm_model_groups, resolve_llm_model_concurrency

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _item(model_id: str) -> SimpleNamespace:
    """Return a stand-in pytest item that records xdist group marks."""
    groups: list[str] = []

    def add_marker(marker: Any) -> None:
        groups.append(marker.mark.args[0])

    return SimpleNamespace(
        callspec=SimpleNamespace(params={"llm_config": {"MODEL_ID": model_id}}),
        groups=groups,
        add_marker=add_marker,
    )


def _groups(items: list[SimpleNamespace]) -> list[str]:
    """Return the xdist group assigned to each item."""
    return [item.groups[0] for item in items]


def test_assign_llm_model_groups_one_slot_per_model() -> None:
    """Concurrency 1 puts every test for a model in the same group."""
    qwen_a = _item("qwen3-8-27b-fp8")
    qwen_b = _item("qwen3-8-27b-fp8")
    glm = _item("glm-5.3")
    assign_llm_model_groups([qwen_a, qwen_b, glm], concurrency=1)
    assert _groups([qwen_a, qwen_b, glm]) == [
        "llm-model-qwen3-8-27b-fp8-0",
        "llm-model-qwen3-8-27b-fp8-0",
        "llm-model-glm-5.3-0",
    ]


def test_assign_llm_model_groups_round_robin_slots() -> None:
    """Concurrency 2 splits one model across two slots and leaves the other model on one."""
    items = [_item("qwen3-8-27b-fp8") for _ in range(3)]
    items.append(_item("glm-5.3"))
    assign_llm_model_groups(items, concurrency=2)
    assert _groups(items) == [
        "llm-model-qwen3-8-27b-fp8-0",
        "llm-model-qwen3-8-27b-fp8-1",
        "llm-model-qwen3-8-27b-fp8-0",
        "llm-model-glm-5.3-0",
    ]


def test_resolve_llm_model_concurrency_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MCP_LLM_MODEL_CONCURRENCY", raising=False)
    assert resolve_llm_model_concurrency(None) == 1


def test_resolve_llm_model_concurrency_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_LLM_MODEL_CONCURRENCY", "2")
    assert resolve_llm_model_concurrency(None) == 2


def test_resolve_llm_model_concurrency_rejects_zero() -> None:
    with pytest.raises(ValueError, match="got 0, want a positive integer"):
        resolve_llm_model_concurrency(0)


def test_xdist_uses_loadgroup_scheduling() -> None:
    """A multi-worker run reports LoadGroupScheduling instead of LoadScheduling."""
    env = os.environ.copy()
    env["DEEPEVAL_TELEMETRY_OPT_OUT"] = "YES"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/mcp_llm_eval/test_llm_model_groups.py",
            "-n",
            "2",
            "-v",
            "-k",
            "not uses_loadgroup",
            "-p",
            "no:cacheprovider",
        ],
        cwd=_PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "scheduling tests via LoadGroupScheduling" in output
