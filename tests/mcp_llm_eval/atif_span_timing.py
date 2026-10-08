"""Rewrite Phoenix LLM and TOOL span times from measured ATIF intervals."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


def format_utc_timestamp(moment: datetime) -> str:
    """Return ``moment`` as an ATIF UTC timestamp with millisecond precision.

    Args:
        moment: Time to format. Naive values are treated as UTC.

    Returns:
        ISO-8601 UTC timestamp with millisecond precision and a ``Z`` suffix.
    """
    if moment.tzinfo is None:
        utc_moment = moment.replace(tzinfo=timezone.utc)
    else:
        utc_moment = moment.astimezone(timezone.utc)
    millisecond = utc_moment.microsecond // 1000
    return utc_moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{millisecond:03d}Z"


def _parse_measured_timestamp(value: Any) -> datetime | None:
    """Parse an ATIF timestamp into aware UTC, or None when it is not a timestamp.

    Args:
        value: Candidate timestamp string.

    Returns:
        Aware UTC datetime, or None when ``value`` is missing or not a string.
    """
    if not isinstance(value, str) or not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _format_span_timestamp(moment: datetime) -> str:
    """Return a Phoenix span timestamp.

    Args:
        moment: Aware or naive UTC time.

    Returns:
        ISO-8601 timestamp with a ``+00:00`` offset, matching the ATIF converter.
    """
    if moment.tzinfo is None:
        utc_moment = moment.replace(tzinfo=timezone.utc)
    else:
        utc_moment = moment.astimezone(timezone.utc)
    return utc_moment.isoformat()


def _measured_interval(start_raw: Any, end_raw: Any) -> tuple[datetime, datetime] | None:
    """Return a start/end pair when both timestamps parse.

    Args:
        start_raw: Interval start timestamp.
        end_raw: Interval end timestamp.

    Returns:
        Aware UTC bounds. The end is raised to the start when it is earlier.
        None when either timestamp is missing.
    """
    start = _parse_measured_timestamp(start_raw)
    end = _parse_measured_timestamp(end_raw)
    if start is None or end is None:
        return None
    return start, max(end, start)


def _shift_tool_after_model(
    start: datetime,
    end: datetime,
    model_end: datetime,
) -> tuple[datetime, datetime]:
    """Keep a tool span strictly after the model span.

    Phoenix sorts sibling spans by start time only. A tool that starts at the
    model end is drawn above the model, so it starts one millisecond later.
    The tool duration is preserved.

    Args:
        start: Recorded tool start.
        end: Recorded tool end.
        model_end: Recorded model end.

    Returns:
        Tool bounds, shifted when they would not sort after the model.
    """
    if start > model_end:
        return start, end
    duration = end - start
    shifted_start = model_end + timedelta(milliseconds=1)
    return shifted_start, shifted_start + duration


def _measured_step_timings(
    trajectories: list[dict[str, Any]],
) -> dict[tuple[Any, Any], dict[str, Any]]:
    """Index model and tool intervals by ``(agent name, step id)``.

    Args:
        trajectories: ATIF trajectories that may carry measured intervals.

    Returns:
        Map of agent name and step id to ``llm`` and ``tools`` intervals.
        Steps with no measured times are omitted.
    """
    timings: dict[tuple[Any, Any], dict[str, Any]] = {}
    for trajectory in trajectories:
        agent = trajectory.get("agent")
        agent_name = agent.get("name") if isinstance(agent, dict) else None
        steps = trajectory.get("steps")
        if not isinstance(steps, list):
            continue
        for step in steps:
            if not isinstance(step, dict) or step.get("source") != "agent":
                continue
            raw_extra = step.get("extra")
            extra = raw_extra if isinstance(raw_extra, dict) else {}
            llm_interval = _measured_interval(extra.get("llm_started_at"), extra.get("llm_ended_at"))
            tool_intervals = _tool_intervals(step.get("tool_calls"))
            if llm_interval is None and not tool_intervals:
                continue
            timings[(agent_name, step.get("step_id"))] = {"llm": llm_interval, "tools": tool_intervals}
    return timings


def _tool_intervals(tool_calls: Any) -> dict[int, tuple[datetime, datetime]]:
    """Return measured intervals keyed by tool-call index.

    Args:
        tool_calls: ATIF ``tool_calls`` list, or anything else.

    Returns:
        Intervals for calls that record both a start and an end.
    """
    intervals: dict[int, tuple[datetime, datetime]] = {}
    if not isinstance(tool_calls, list):
        return intervals
    for index, tool_call in enumerate(tool_calls):
        if not isinstance(tool_call, dict):
            continue
        raw_extra = tool_call.get("extra")
        call_extra = raw_extra if isinstance(raw_extra, dict) else {}
        interval = _measured_interval(call_extra.get("started_at"), call_extra.get("ended_at"))
        if interval is not None:
            intervals[index] = interval
    return intervals


def _span_kind_and_metadata(span: dict[str, Any]) -> tuple[Any, dict[str, Any]] | None:
    """Return a span's kind and metadata dict, or None when metadata is absent.

    Args:
        span: One converted Phoenix span.

    Returns:
        ``(kind, metadata)`` or None.
    """
    attributes = span.get("attributes")
    if not isinstance(attributes, dict):
        return None
    metadata = attributes.get("metadata")
    if not isinstance(metadata, dict):
        return None
    kind = span.get("span_kind")
    if kind is None:
        kind = attributes.get("openinference.span.kind")
    return kind, metadata


def _as_interval(value: Any) -> tuple[datetime, datetime] | None:
    """Return ``value`` when it is a two-datetime interval."""
    if isinstance(value, tuple) and len(value) == 2 and all(isinstance(bound, datetime) for bound in value):
        return value
    return None


def _tool_interval_for_span(
    metadata: dict[str, Any],
    measured: dict[str, Any],
) -> tuple[datetime, datetime] | None:
    """Return the tool interval for one span, starting after the model when needed.

    Args:
        metadata: Span metadata containing ``atif.tool_call_index``.
        measured: Measured ``llm`` interval and ``tools`` map for the step.

    Returns:
        Tool bounds, or None when this span has no measured tool interval.
    """
    tool_index = metadata.get("atif.tool_call_index")
    if isinstance(tool_index, bool) or not isinstance(tool_index, int):
        return None
    tools = measured.get("tools")
    if not isinstance(tools, dict):
        return None
    interval = _as_interval(tools.get(tool_index))
    if interval is None:
        return None
    model_interval = _as_interval(measured.get("llm"))
    if model_interval is None:
        return interval
    return _shift_tool_after_model(interval[0], interval[1], model_interval[1])


def _interval_for_span(
    kind: Any,
    metadata: dict[str, Any],
    measured: dict[str, Any],
) -> tuple[datetime, datetime] | None:
    """Return the measured interval for an LLM or TOOL span.

    Args:
        kind: Phoenix span kind.
        metadata: Span metadata used to match a tool call.
        measured: Measured intervals for the ATIF step.

    Returns:
        Bounds to write onto the span, or None when this span is not rewritten.
    """
    if kind == "LLM":
        return _as_interval(measured.get("llm"))
    if kind == "TOOL":
        return _tool_interval_for_span(metadata, measured)
    return None


def apply_measured_span_times(
    spans: list[Any],
    trajectories: list[dict[str, Any]],
) -> None:
    """Rewrite LLM and TOOL span bounds from intervals recorded on ATIF steps.

    Phoenix's ATIF converter emits both as zero-duration events at the step
    timestamp, so the trace tree lists the tool before the model. Measured
    intervals restore model-then-tool order and the model's real duration.
    CHAIN and AGENT spans are left unchanged.

    Args:
        spans: Converted Phoenix spans, mutated in place.
        trajectories: Source ATIF trajectories used to convert ``spans``.
    """
    timings = _measured_step_timings(trajectories)
    for span in spans:
        if not isinstance(span, dict):
            continue
        resolved = _span_kind_and_metadata(span)
        if resolved is None:
            continue
        kind, metadata = resolved
        measured = timings.get((metadata.get("agent_name"), metadata.get("atif.step_id")))
        if not isinstance(measured, dict):
            continue
        interval = _interval_for_span(kind, metadata, measured)
        if interval is None:
            continue
        start, end = interval
        span["start_time"] = _format_span_timestamp(start)
        span["end_time"] = _format_span_timestamp(end)
        metadata["atif.timing"] = "measured"
