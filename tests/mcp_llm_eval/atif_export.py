"""Build ATIF trajectories from LLM tests and optionally upload them to Phoenix."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from phoenix.client import Client
    from phoenix.client.helpers.atif import (  # pylint: disable=protected-access
        _convert_atif_trajectories_to_spans,
    )
except ImportError:  # pragma: no cover - optional runtime dependency
    Client = None  # type: ignore[misc, assignment]
    _convert_atif_trajectories_to_spans = None  # type: ignore[misc, assignment]

DISABLE_TRACE_EXPORT_ENV = "INSIGHTS_MCP_DISABLE_TRACE_EXPORT"
PHOENIX_COLLECTOR_ENDPOINT_ENV = "PHOENIX_COLLECTOR_ENDPOINT"
PHOENIX_PROJECT_PREFIX = "insights-mcp-test-"
ATIF_SCHEMA_VERSION = "ATIF-v1.7"
FAILED_PYTEST_OUTCOMES = frozenset({"failed", "error"})
_TRUTHY_ENV_VALUES = frozenset({"1", "true", "yes", "on"})
MISSING_PHOENIX_CLIENT = (
    "arize-phoenix-client is not installed. Unset PHOENIX_COLLECTOR_ENDPOINT or uv pip install arize-phoenix-client"
)

_TESTS_DIR = Path(__file__).resolve().parents[1]
DEFAULT_LOGS_DIR = _TESTS_DIR / "logs"


def _is_truthy_env(value: str) -> bool:
    """Return True when an env value is a conventional truthy flag."""
    return value.strip().lower() in _TRUTHY_ENV_VALUES


def trace_export_disabled() -> bool:
    """Return True when ATIF file export and Phoenix upload are disabled.

    Returns:
        True if ``INSIGHTS_MCP_DISABLE_TRACE_EXPORT`` is a truthy value.
    """
    return _is_truthy_env(os.getenv(DISABLE_TRACE_EXPORT_ENV, ""))


def phoenix_collector_endpoint() -> str:
    """Return ``PHOENIX_COLLECTOR_ENDPOINT`` or an empty string if unset.

    Returns:
        Collector base URL with trailing whitespace stripped.
    """
    return os.getenv(PHOENIX_COLLECTOR_ENDPOINT_ENV, "").strip()


def default_logs_dir() -> Path:
    """Return the default ``tests/logs`` directory.

    Returns:
        Absolute path to ``tests/logs``.
    """
    return DEFAULT_LOGS_DIR


def phoenix_project_name(run_id: str) -> str:
    """Return the Phoenix project name for a testrun folder.

    Args:
        run_id: Fourteen-digit testrun id (YYYYMMDDhhmmss).

    Returns:
        Project name ``insights-mcp-<run_id>``.
    """
    return f"{PHOENIX_PROJECT_PREFIX}{run_id}"


def require_phoenix_client() -> None:
    """Raise if the optional Phoenix client is not installed.

    Raises:
        RuntimeError: When ``phoenix.client`` cannot be imported.
    """
    if Client is None or _convert_atif_trajectories_to_spans is None:
        raise RuntimeError(MISSING_PHOENIX_CLIENT)


def ensure_phoenix_ready() -> None:
    """Fail fast when live Phoenix upload is requested without the client.

    Raises:
        RuntimeError: If ``PHOENIX_COLLECTOR_ENDPOINT`` is set and the package is missing.
    """
    if trace_export_disabled():
        return
    if phoenix_collector_endpoint():
        require_phoenix_client()


def node_display_id(node_id: str) -> str:
    """Return ``Class::test[params]`` from a full pytest node id.

    Args:
        node_id: Full pytest node id, including the module path.

    Returns:
        Node id without the ``path/to/file.py::`` prefix, safe as a filename stem.
    """
    marker = ".py::"
    index = node_id.rfind(marker)
    if index >= 0:
        prefix_end = index + len(marker)
        return node_id[prefix_end:]
    return node_id.rsplit("/", 1)[-1]


def node_test_id(display_id: str) -> str:
    """Return ``Class::test`` without a trailing pytest param block.

    Args:
        display_id: ``Class::test[params]`` from ``node_display_id``.

    Returns:
        Unparametrized test id. Unchanged when there is no ``[...]`` suffix.
    """
    if display_id.endswith("]"):
        bracket = display_id.rfind("[")
        if bracket > 0:
            return display_id[:bracket]
    return display_id


def utc_timestamp() -> str:
    """Return the current UTC time as an ATIF timestamp.

    Returns:
        ISO-8601 UTC timestamp with millisecond precision and a ``Z`` suffix.
    """
    now = datetime.now(timezone.utc)
    millisecond = now.microsecond // 1000
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{millisecond:03d}Z"


def session_run_id() -> str:
    """Return a new fourteen-digit testrun id.

    Returns:
        ``YYYYMMDDhhmmss`` in UTC.
    """
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def atif_session_id(run_id: str, display_id: str) -> str:
    """Return an ATIF session id shared by all params of one pytest test function.

    Phoenix derives trace_id from session_id. Parametrized nodes of the same
    ``Class::test`` share a trace; AGENT roots stay distinct via trajectory_id.

    Args:
        run_id: Fourteen-digit testrun id (YYYYMMDDhhmmss).
        display_id: ``Class::test[params]`` from ``node_display_id``.

    Returns:
        ``{run_id}::{Class::test}``.
    """
    return f"{run_id}::{node_test_id(display_id)}"


def _trajectory_extra(trajectory: dict[str, Any]) -> dict[str, Any]:
    """Merge trajectory-level and agent-level extra maps.

    Args:
        trajectory: Parsed ATIF trajectory.

    Returns:
        Combined extra dict; agent extra overrides trajectory extra on key collisions.
    """
    extra: dict[str, Any] = {}
    extra.update(trajectory.get("extra") or {})
    agent = trajectory.get("agent")
    if isinstance(agent, dict):
        extra.update(agent.get("extra") or {})
    return extra


def apply_pytest_span_status(
    spans: list[Any],
    trajectories: list[dict[str, Any]],
) -> None:
    """Set Phoenix root-span status from pytest outcome stored in ATIF extra.

    Phoenix's ATIF importer always writes status_code OK. Failed tests are
    marked ERROR on the AGENT root so they show in the project status column.

    Args:
        spans: Converted Phoenix spans (TypedDict/dict, mutated in place).
        trajectories: Source ATIF trajectories used to convert ``spans``.
    """
    failed_by_name: dict[str, str] = {}
    for trajectory in trajectories:
        extra = _trajectory_extra(trajectory)
        outcome = str(extra.get("pytest_outcome", extra.get("test_status", "passed"))).lower()
        if outcome not in FAILED_PYTEST_OUTCOMES:
            continue
        agent = trajectory.get("agent")
        if not isinstance(agent, dict):
            continue
        agent_name = agent.get("name")
        if not isinstance(agent_name, str) or not agent_name:
            continue
        failed_by_name[agent_name] = str(
            extra.get("pytest_status_message") or extra.get("failure_message") or "pytest failed"
        )

    for span in spans:
        if span.get("parent_id") is not None:
            continue
        attributes = span.get("attributes") or {}
        kind = span.get("span_kind") or attributes.get("openinference.span.kind")
        if kind != "AGENT":
            continue
        name = span.get("name")
        if name not in failed_by_name:
            continue
        span["status_code"] = "ERROR"
        span["status_message"] = failed_by_name[name]


def upload_trajectories(
    trajectories: list[dict[str, Any]],
    *,
    project_name: str,
    endpoint: str,
) -> Any:
    """Convert ATIF trajectories to Phoenix spans and upload them.

    Args:
        trajectories: ATIF trajectory dicts.
        project_name: Phoenix project identifier.
        endpoint: Phoenix collector base URL.

    Returns:
        Response body from ``log_spans``.

    Raises:
        RuntimeError: If the Phoenix client is not installed.
    """
    require_phoenix_client()
    os.environ[PHOENIX_COLLECTOR_ENDPOINT_ENV] = endpoint
    convert = _convert_atif_trajectories_to_spans
    client_cls = Client
    if convert is None or client_cls is None:  # pragma: no cover - guarded by require_phoenix_client
        raise RuntimeError(MISSING_PHOENIX_CLIENT)
    spans = convert(trajectories)
    apply_pytest_span_status(spans, trajectories)
    return client_cls().spans.log_spans(project_identifier=project_name, spans=spans)


def write_atif_json(path: Path, trajectory: dict[str, Any]) -> None:
    """Write one ATIF trajectory as pretty-printed JSON.

    Args:
        path: Destination file.
        trajectory: ATIF trajectory object.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(trajectory, indent=2, ensure_ascii=False)
    path.write_text(encoded + "\n", encoding="utf-8")


def tool_definitions_from_tools(tools: list[Any] | None) -> list[dict[str, Any]]:
    """Map LlamaIndex/MCP tools to ATIF ``tool_definitions``.

    Args:
        tools: Agent tool objects, or None.

    Returns:
        ATIF function tool definitions. Unknown schema shapes become empty objects.
    """
    definitions: list[dict[str, Any]] = []
    for tool in tools or []:
        metadata = getattr(tool, "metadata", None)
        name = str(getattr(metadata, "name", None) or getattr(tool, "name", "") or "")
        description = str(getattr(metadata, "description", None) or "")
        parameters: dict[str, Any] = {"type": "object", "properties": {}}
        fn_schema = getattr(metadata, "fn_schema", None)
        if fn_schema is not None and hasattr(fn_schema, "model_json_schema"):
            schema = fn_schema.model_json_schema()
            if isinstance(schema, dict):
                parameters = {
                    key: schema[key] for key in ("type", "properties", "required") if key in schema
                } or parameters
        definitions.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": parameters,
                },
            }
        )
    return definitions


def _tool_output_content(tool_output: Any) -> str:
    """Stringify a LlamaIndex ``ToolOutput`` (or test double) for ATIF observations."""
    if tool_output is None:
        return ""
    content = getattr(tool_output, "content", None)
    if isinstance(content, str) and content:
        return content
    texts: list[str] = []
    for block in getattr(tool_output, "blocks", None) or []:
        text = getattr(block, "text", None)
        if text:
            texts.append(str(text))
    if texts:
        return "\n".join(texts)
    raw_output = getattr(tool_output, "raw_output", None)
    if raw_output is None or isinstance(raw_output, (bytes, bytearray)):
        return str(tool_output)
    if isinstance(raw_output, str):
        return raw_output
    try:
        dumped = json.dumps(raw_output, ensure_ascii=False)
    except TypeError:
        dumped = str(raw_output)
    return dumped


def _message_text(message: Any) -> str:
    """Extract display text from a chat message or similar object."""
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


def _response_message_text(event: Any) -> str:
    """Extract assistant text from an ``AgentOutput``-like event."""
    return _message_text(getattr(event, "response", None))


def _role_name(role: Any) -> str:
    """Return a chat role string from an enum or plain value."""
    if role is None:
        return ""
    value = getattr(role, "value", role)
    return str(value)


def _serialize_llm_input(messages: Any) -> list[dict[str, str]]:
    """Serialize ``AgentInput.input`` chat messages to role/content dicts."""
    serialized: list[dict[str, str]] = []
    for message in messages or []:
        serialized.append(
            {
                "role": _role_name(getattr(message, "role", "")),
                "content": _message_text(message),
            }
        )
    return serialized


def _int_token_count(value: Any) -> int | None:
    """Return a non-boolean int token count, or None if missing/invalid."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def _token_count(container: Any, *names: str) -> int | None:
    """Read the first present token-count field from a dict or object."""
    for name in names:
        if isinstance(container, dict):
            value = container.get(name)
        else:
            value = getattr(container, name, None)
        parsed = _int_token_count(value)
        if parsed is not None:
            return parsed
    return None


def _usage_container(obj: Any) -> Any:
    """Return a usage mapping/object nested under ``usage``, or ``obj`` itself."""
    if obj is None:
        return None
    nested = obj.get("usage") if isinstance(obj, dict) else getattr(obj, "usage", None)
    if nested is not None:
        return nested
    prompt_tokens = _token_count(obj, "prompt_tokens")
    completion_tokens = _token_count(obj, "completion_tokens")
    if prompt_tokens is not None or completion_tokens is not None:
        return obj
    return None


def _usage_from_event(event: Any) -> dict[str, int] | None:
    """Extract OpenAI-like prompt/completion tokens from an agent event.

    Args:
        event: ``AgentOutput`` (or stream event) with optional ``raw`` usage.

    Returns:
        Metrics dict with only fields the provider supplied, or None.
    """
    candidates = (
        getattr(event, "raw", None),
        getattr(getattr(event, "response", None), "raw", None),
        getattr(getattr(event, "response", None), "additional_kwargs", None),
        getattr(event, "additional_kwargs", None),
    )
    for candidate in candidates:
        usage = _usage_container(candidate)
        if usage is None:
            continue
        metrics: dict[str, int] = {}
        prompt_tokens = _token_count(usage, "prompt_tokens")
        completion_tokens = _token_count(usage, "completion_tokens")
        if prompt_tokens is not None:
            metrics["prompt_tokens"] = prompt_tokens
        if completion_tokens is not None:
            metrics["completion_tokens"] = completion_tokens
        if metrics:
            return metrics
    return None


def _tool_call_dict(event: Any) -> dict[str, Any]:
    """Map a ToolCall event or ToolSelection to an ATIF tool_call object."""
    return {
        "tool_call_id": str(getattr(event, "tool_id", "")),
        "function_name": str(getattr(event, "tool_name", "")),
        "arguments": dict(getattr(event, "tool_kwargs", None) or {}),
    }


class AtifTrajectoryBuilder:  # pylint: disable=too-many-instance-attributes
    """Accumulate ATIF steps from one LLM test (possibly multiple user turns)."""

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        *,
        session_id: str,
        trajectory_id: str,
        pytest_node_id: str,
        model_name: str,
        tool_definitions: list[dict[str, Any]],
        test_file: str,
        test_line: int,
        testrun: str | None = None,
    ) -> None:
        self.session_id = session_id
        self.testrun = testrun if testrun is not None else session_id
        self.trajectory_id = trajectory_id
        self.pytest_node_id = pytest_node_id
        self.model_name = model_name
        self.tool_definitions = tool_definitions
        self.test_file = test_file
        self.test_line = test_line
        self._steps: list[dict[str, Any]] = []
        self._turn_start_index = 0
        self._pending_tool_calls: list[dict[str, Any]] = []
        self._pending_observations: list[dict[str, Any]] = []
        self._pending_thinking = ""
        self._pending_llm_input: list[dict[str, str]] = []
        self._pending_metrics: dict[str, int] = {}
        self._outcome = "passed"
        self._status_message = ""

    def has_steps(self) -> bool:
        """Return True when at least one ATIF step has been recorded."""
        return bool(self._steps) or bool(self._pending_tool_calls) or bool(self._pending_thinking.strip())

    def begin_turn(self, user_msg: str) -> None:
        """Start a user turn, flushing any pending agent step first.

        Args:
            user_msg: Prompt actually sent to the agent, including MCP instructions when injected.
        """
        self._flush_pending_agent_step("")
        self._turn_start_index = len(self._steps)
        self._steps.append(self._make_step(source="user", message=user_msg))

    def reset_turn(self, user_msg: str) -> None:
        """Drop the current turn (used on empty-response retry) and start it again.

        Args:
            user_msg: Prompt sent to the agent.
        """
        self._clear_pending_agent_state()
        self._steps = self._steps[: self._turn_start_index]
        self.begin_turn(user_msg)

    def consume_event(self, event: Any) -> None:
        """Record a workflow stream event as ATIF tool calls, observations, or messages.

        Args:
            event: LlamaIndex workflow event or a test double with the same class name.
        """
        event_name = type(event).__name__
        if event_name == "AgentInput":
            self._consume_agent_input(event)
            return
        if event_name == "AgentStream":
            thinking_delta = getattr(event, "thinking_delta", None)
            if isinstance(thinking_delta, str) and thinking_delta:
                self._pending_thinking += thinking_delta
            return
        if event_name == "ToolCall":
            self._consume_tool_call(event)
            return
        if event_name == "ToolCallResult":
            call_id = str(getattr(event, "tool_id", ""))
            self._pending_observations.append(
                {
                    "source_call_id": call_id,
                    "content": _tool_output_content(getattr(event, "tool_output", None)),
                }
            )
            return
        if event_name == "AgentOutput":
            self._consume_agent_output(event)

    def finish(
        self,
        *,
        pytest_outcome: str,
        pytest_status_message: str = "",
    ) -> dict[str, Any]:
        """Build the ATIF trajectory object.

        Args:
            pytest_outcome: Pytest call outcome (``passed``, ``failed``, ``skipped``).
            pytest_status_message: Failure representation; empty on success.

        Returns:
            ATIF trajectory dict ready to serialize.
        """
        self._flush_pending_agent_step("")
        self._outcome = pytest_outcome
        self._status_message = pytest_status_message
        extra = self._common_extra()
        extra["testrun"] = self.testrun
        if pytest_status_message:
            extra["pytest_status_message"] = pytest_status_message
        for step in self._steps:
            step_extra = dict(step.get("extra") or {})
            step_extra.update(self._location_extra())
            step_extra["pytest_outcome"] = pytest_outcome
            step["extra"] = step_extra
        return {
            "schema_version": ATIF_SCHEMA_VERSION,
            "session_id": self.session_id,
            "trajectory_id": self.trajectory_id,
            "agent": {
                "name": self.trajectory_id,
                "version": "0.0.0",
                "model_name": self.model_name,
                "tool_definitions": self.tool_definitions,
                "extra": extra,
            },
            "notes": self.pytest_node_id,
            "extra": extra,
            "final_metrics": {"total_steps": len(self._steps)},
            "steps": self._steps,
        }

    def _location_extra(self) -> dict[str, Any]:
        return {
            "pytest_node_id": self.pytest_node_id,
            "test_file": self.test_file,
            "test_line": self.test_line,
        }

    def _common_extra(self) -> dict[str, Any]:
        extra = self._location_extra()
        extra["pytest_outcome"] = self._outcome
        return extra

    def _make_step(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        *,
        source: str,
        message: str,
        tool_calls: list[dict[str, Any]] | None = None,
        observation_results: list[dict[str, Any]] | None = None,
        reasoning_content: str = "",
        metrics: dict[str, int] | None = None,
        llm_input: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        extra = self._location_extra()
        if llm_input:
            extra["llm_input"] = llm_input
        step: dict[str, Any] = {
            "step_id": len(self._steps) + 1,
            "timestamp": utc_timestamp(),
            "source": source,
            "message": message,
            "extra": extra,
        }
        if source == "agent":
            step["model_name"] = self.model_name
        if reasoning_content:
            step["reasoning_content"] = reasoning_content
        if metrics:
            step["metrics"] = metrics
        if tool_calls:
            step["tool_calls"] = tool_calls
        if observation_results:
            step["observation"] = {"results": observation_results}
        return step

    def _pending_round_complete(self) -> bool:
        return bool(self._pending_tool_calls) and (len(self._pending_observations) >= len(self._pending_tool_calls))

    def _clear_pending_agent_state(self) -> None:
        self._pending_tool_calls = []
        self._pending_observations = []
        self._pending_thinking = ""
        self._pending_llm_input = []
        self._pending_metrics = {}

    def _record_tool_call(self, tool_call: dict[str, Any]) -> None:
        call_id = tool_call.get("tool_call_id", "")
        if call_id:
            for existing in self._pending_tool_calls:
                if existing.get("tool_call_id") == call_id:
                    return
        self._pending_tool_calls.append(tool_call)

    def _consume_agent_input(self, event: Any) -> None:
        if self._pending_round_complete() or self._pending_thinking.strip() or self._pending_metrics:
            self._flush_pending_agent_step("")
        self._pending_llm_input = _serialize_llm_input(getattr(event, "input", None))

    def _consume_tool_call(self, event: Any) -> None:
        if self._pending_round_complete():
            self._flush_pending_agent_step("")
        self._record_tool_call(_tool_call_dict(event))

    def _consume_agent_output(self, event: Any) -> None:
        usage = _usage_from_event(event)
        if usage:
            self._pending_metrics.update(usage)
        for selection in getattr(event, "tool_calls", None) or []:
            self._record_tool_call(_tool_call_dict(selection))
        message = _response_message_text(event)
        has_thinking = bool(self._pending_thinking.strip())
        if message.strip() or self._pending_tool_calls or has_thinking or self._pending_metrics:
            self._flush_pending_agent_step(message)

    def _flush_pending_agent_step(self, message: str) -> None:
        has_message = bool(message.strip())
        has_tools = bool(self._pending_tool_calls)
        has_thinking = bool(self._pending_thinking.strip())
        has_metrics = bool(self._pending_metrics)
        if not (has_message or has_tools or has_thinking or has_metrics):
            return
        self._steps.append(
            self._make_step(
                source="agent",
                message=message,
                tool_calls=self._pending_tool_calls or None,
                observation_results=self._pending_observations or None,
                reasoning_content=self._pending_thinking,
                metrics=self._pending_metrics or None,
                llm_input=self._pending_llm_input or None,
            )
        )
        self._clear_pending_agent_state()
