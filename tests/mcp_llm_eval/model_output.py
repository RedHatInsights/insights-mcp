"""JSON-safe dumps of model turns, including thinking blocks and provider extras."""

from __future__ import annotations

import json
from typing import Any


def message_text(message: Any) -> str:
    """Extract display text from a chat message or similar object.

    Args:
        message: Chat message, plain string, or None.

    Returns:
        String content or text-block text. Thinking blocks and non-string content are omitted.
    """
    if message is None:
        return ""
    content = getattr(message, "content", None)
    if isinstance(content, str) and content:
        return content
    texts: list[str] = []
    for block in getattr(message, "blocks", None) or []:
        text = getattr(block, "text", None)
        if text:
            texts.append(str(text))
    if texts:
        return "\n".join(texts)
    if isinstance(message, str):
        return message
    return ""


def _is_thinking_block(block: Any) -> bool:
    """Return True for LlamaIndex reasoning blocks, which store text on ``content``."""
    if getattr(block, "block_type", None) == "thinking":
        return True
    return type(block).__name__ == "ThinkingBlock"


def thinking_text(message: Any) -> str:
    """Join reasoning text stored on thinking blocks.

    Args:
        message: Chat message or test double. Missing blocks yield an empty string.

    Returns:
        Thinking block text. Non-string block content is included via ``repr``.
    """
    parts: list[str] = []
    for block in getattr(message, "blocks", None) or []:
        if not _is_thinking_block(block):
            continue
        content = getattr(block, "content", None)
        if isinstance(content, str) and content:
            parts.append(content)
        elif content not in (None, ""):
            parts.append(repr(content))
    return "\n".join(parts)


def merge_thinking(existing: str, extra: str) -> str:
    """Combine stream thinking with block thinking without duplicating one inside the other.

    Args:
        existing: Reasoning already accumulated, often from stream deltas.
        extra: Additional reasoning, often from a thinking block.

    Returns:
        The longer text when one contains the other, otherwise both joined by a newline.
    """
    if not extra:
        return existing
    if not existing or existing in extra:
        return extra
    if extra in existing:
        return existing
    return f"{existing}\n{extra}"


def _model_dump_value(value: Any) -> Any:
    """Return ``model_dump`` output when present, otherwise ``value``.

    Args:
        value: Provider object or already plain data.

    Returns:
        Dumped data, the original value, or ``repr`` when dumping fails.
    """
    model_dump = getattr(value, "model_dump", None)
    if not callable(model_dump):
        return value
    try:
        try:
            return model_dump(mode="json")
        except TypeError:
            return model_dump()
    except Exception:  # pylint: disable=broad-exception-caught
        return repr(value)


def _json_safe_container(value: Any) -> Any:
    """Walk a container that ``json.dumps`` rejected and replace non-JSON leaves with ``repr``."""
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return repr(value)


def json_safe(value: Any) -> Any:
    """Return a JSON-serializable copy, using ``repr`` for values that cannot be encoded.

    Args:
        value: Provider payload, message content, or a pydantic model.

    Returns:
        A structure ``json.dumps`` can encode, or a ``repr`` string.
    """
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (bytes, bytearray)):
        return repr(value)
    prepared = _model_dump_value(value)
    try:
        json.dumps(prepared)
    except TypeError:
        prepared = _json_safe_container(prepared)
    return prepared


def _blocks_dump(message: Any) -> list[dict[str, Any]]:
    """Serialize chat blocks, including thinking content and unrecognized shapes."""
    dumped: list[dict[str, Any]] = []
    for block in getattr(message, "blocks", None) or []:
        block_type = getattr(block, "block_type", None) or type(block).__name__
        entry: dict[str, Any] = {"block_type": str(block_type)}
        text = getattr(block, "text", None)
        if text is not None:
            entry["text"] = text if isinstance(text, str) else repr(text)
        content = getattr(block, "content", None)
        if content is not None and (_is_thinking_block(block) or "text" not in entry):
            entry["content"] = content if isinstance(content, str) else json_safe(content)
        additional = getattr(block, "additional_information", None)
        if additional:
            entry["additional_information"] = json_safe(additional)
        if "text" not in entry and "content" not in entry:
            entry["repr"] = repr(block)
        dumped.append(entry)
    return dumped


def model_output_dump(message: Any, raw: Any = None, thinking: str = "") -> dict[str, Any]:
    """Build a JSON-safe record of one model turn, including dropped reasoning and raw extras.

    Visible assistant text stays separate from thinking. Non-string ``content`` is kept
    so a list or other unexpected shape is not discarded. Pydantic ``raw`` values are
    dumped with ``model_dump`` so provider extra keys such as ``thinking`` survive.

    Args:
        message: Assistant chat message, or None.
        raw: Provider response (dict or pydantic model). None omits the field.
        thinking: Reasoning already accumulated from stream deltas.

    Returns:
        Dump with only the fields that were present. Empty when nothing was captured.
    """
    visible_text = message_text(message)
    merged_thinking = merge_thinking(thinking, thinking_text(message))
    dump: dict[str, Any] = {}
    if visible_text:
        dump["visible_text"] = visible_text
    if merged_thinking:
        dump["thinking"] = merged_thinking
    content = getattr(message, "content", None) if message is not None else None
    if not isinstance(content, str) and content is not None:
        dump["content"] = json_safe(content)
    blocks = _blocks_dump(message)
    if blocks:
        dump["blocks"] = blocks
    additional_kwargs = getattr(message, "additional_kwargs", None) if message is not None else None
    if additional_kwargs:
        dump["additional_kwargs"] = json_safe(additional_kwargs)
    if raw is not None:
        dump["raw"] = json_safe(raw)
    return dump


def render_model_output(dump: dict[str, Any]) -> str:
    """Serialize a model-output dump for logs and for Phoenix, which reads ``step.message``.

    Args:
        dump: Result of ``model_output_dump``.

    Returns:
        JSON text, or ``repr`` if the dump still cannot be encoded. Empty when ``dump`` is empty.
    """
    if not dump:
        return ""
    try:
        return json.dumps(dump, ensure_ascii=False, sort_keys=True)
    except TypeError:
        return repr(dump)
