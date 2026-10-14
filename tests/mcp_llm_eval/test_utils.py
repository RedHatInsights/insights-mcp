"""Unit tests for tests.mcp_llm_eval.utils helpers."""

from tests.mcp_llm_eval.utils import ABBREVIATED_LOG_MARKER, abbreviate_middle


def test_abbreviate_middle_short_text_unchanged() -> None:
    text = "short failure message"
    assert abbreviate_middle(text) == text


def test_abbreviate_middle_long_text_contains_marker() -> None:
    text = "x" * 3000
    abbreviated = abbreviate_middle(text)
    assert ABBREVIATED_LOG_MARKER in abbreviated
    assert len(abbreviated) < len(text)


def test_abbreviate_middle_long_text_preserves_head_and_tail() -> None:
    head = "HEAD" * 600
    tail = "TAIL" * 600
    text = head + ("middle" * 200) + tail
    abbreviated = abbreviate_middle(text)
    half = 2000 // 2
    assert abbreviated.startswith(head[:half])
    assert abbreviated.endswith(tail[-half:])
