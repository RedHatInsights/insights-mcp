"""LlamaIndex MCP agent used by behavioral integration tests."""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import httpx
import requests
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.agent.workflow.workflow_events import AgentOutput
from llama_index.core.llms import ChatMessage
from llama_index.core.tools import BaseTool
from llama_index.core.workflow import Context
from llama_index.llms.openai_like import OpenAILike
from llama_index.tools.mcp import BasicMCPClient, McpToolSpec
from mcp.shared._httpx_utils import create_mcp_http_client

from deepeval_support.tool_calls import tool_call_record
from instrumentation_tests.mcp_jsonrpc import (
    DEFAULT_JSON_HEADERS,
    create_mcp_init_request,
    parse_mcp_response,
)


def _message_text(message: ChatMessage) -> str:
    """Return plain text from a ChatMessage content field."""
    content = message.content
    if isinstance(content, str):
        return content
    if content is None:
        return ""
    return str(content)


def _embed_chat_history_in_user_message(user_msg: str, messages: List[ChatMessage]) -> Tuple[str, List[ChatMessage]]:
    """Fold prior turns into the user message when multi-turn replay breaks a gateway."""
    lines: List[str] = []
    for message in messages:
        text = _message_text(message).strip()
        if text:
            lines.append(f"{message.role}: {text}")
    if not lines:
        return user_msg, []
    embedded = "Previous conversation:\n" + "\n".join(lines) + f"\n\nCurrent request: {user_msg}"
    return embedded, []


def _is_paging_followup(user_msg: str, messages: List[ChatMessage]) -> bool:
    """Return True when the user is asking for the next page of a prior list."""
    if not messages:
        return False
    lowered = user_msg.lower()
    return any(token in lowered for token in ("next", "more", "another page", "show me the next"))


def _paging_followup_user_message(user_msg: str) -> str:
    """Nudge the model to call get_blueprints with limit/offset instead of answering from memory."""
    return (
        f"{user_msg}\n\n"
        "Use image-builder__get_blueprints with the requested limit and offset "
        "(for example offset=2 after listing 2 items). Do not answer from conversation memory alone."
    )


def _compact_chat_history_for_followup(messages: List[ChatMessage]) -> List[ChatMessage]:
    """Keep user/assistant text only; drop tool replay that breaks strict gateways (e.g. Gemini Pro)."""
    compact: List[ChatMessage] = []
    for message in messages:
        if message.role == "system":
            continue
        if message.role == "tool":
            continue
        if message.role == "assistant":
            extra = getattr(message, "additional_kwargs", None) or {}
            if extra.get("tool_calls") and not _message_text(message).strip():
                continue
            text = _message_text(message).strip()
            if text:
                compact.append(ChatMessage(role="assistant", content=text))
            continue
        if message.role == "user":
            text = _message_text(message).strip()
            if text:
                compact.append(ChatMessage(role="user", content=text))
    return compact


def _chat_message_text(message: ChatMessage) -> str:
    """Extract display text from a ChatMessage (content string or text blocks)."""
    content = message.content
    if isinstance(content, str) and content:
        return content
    block_texts: List[str] = []
    for block in getattr(message, "blocks", None) or []:
        text = getattr(block, "text", None)
        if text:
            block_texts.append(text)
    return "\n".join(block_texts)


def _assistant_text_from_handler_response(response: Any) -> str:
    """Normalize workflow handler output to plain assistant text for chat history."""
    if isinstance(response, AgentOutput):
        return _chat_message_text(response.response)
    if hasattr(response, "response") and hasattr(response.response, "content"):
        return _chat_message_text(response.response)
    if response is None:
        return ""
    return str(response)


class MCPAgentWrapper:  # pylint: disable=too-many-instance-attributes
    """MCP agent wrapper that records tool calls and step progression.

    - Records tool calls for validation in tests
    - Optionally logs step progression if a logger is provided
    - Provides minimal reasoning steps useful for debugging output
    """

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def __init__(
        self,
        server_url: str,
        api_url: str,
        model_id: str,
        api_key: str,
        verbose_logger: Optional[logging.Logger] = None,
    ):  # pylint: disable=too-many-instance-attributes
        self.server_url = server_url
        self.api_url = api_url
        self.model_id = model_id
        self.api_key = api_key
        self.tools: Optional[List[Union[BaseTool, Callable]]] = []
        self.system_prompt = ""
        self.agent: Optional[FunctionAgent] = None
        self.context: Optional[Context] = None

        self._called_tools: List[Any] = []
        self._step_names: List[str] = []
        self._mcp_client: Optional[BasicMCPClient] = None
        self._llm_http_client: Optional[httpx.AsyncClient] = None
        self._initialized = False
        self.llama_llm: Optional[OpenAILike] = None

        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        if verbose_logger:
            self.logger = verbose_logger

    async def initialize(self) -> None:
        """Initialize MCP session and agent on the caller's event loop."""
        if self._initialized:
            return
        self._llm_http_client = httpx.AsyncClient(timeout=httpx.Timeout(60.0))
        # parallel_tool_calls is enforced via FunctionAgent.allow_parallel_tool_calls;
        # omit it here because some OpenAI-compatible gateways (e.g. Gemini Flash) reject the field.
        self.llama_llm = OpenAILike(
            model=self.model_id,
            api_base=self.api_url,
            api_key=self.api_key,
            temperature=0.1,
            context_window=8192,
            max_tokens=2048,
            is_chat_model=True,
            is_function_calling_model=True,
            async_http_client=self._llm_http_client,
        )
        await self._init_mcp_tools()
        await self._setup_agent()
        self._initialized = True

    async def aclose(self) -> None:
        """Close HTTP clients before the event loop shuts down."""
        aclient = getattr(self.llama_llm, "_aclient", None) if self.llama_llm is not None else None
        if aclient is not None:
            await aclient.close()
        elif self._llm_http_client is not None:
            await self._llm_http_client.aclose()
        if self._mcp_client is not None:
            await self._mcp_client.http_client.aclose()
        self._llm_http_client = None
        self._mcp_client = None
        self._initialized = False

    async def _init_mcp_tools(self):
        """Initialize MCP tools using LlamaIndex MCP support."""
        try:
            if self.server_url == "stdio":
                mcp_client = BasicMCPClient("python", args=["-m", "insights_mcp.server", "stdio"])
                fetch_system_prompt = False
            else:
                mcp_http_client = create_mcp_http_client(headers=None)
                mcp_client = BasicMCPClient(self.server_url, http_client=mcp_http_client)
                fetch_system_prompt = self.server_url.startswith("http")
            self._mcp_client = mcp_client
            mcp_tool_spec = McpToolSpec(client=mcp_client)
            self.tools = await mcp_tool_spec.to_tool_list_async()

            if fetch_system_prompt:
                self.system_prompt = await self._get_system_prompt()
            else:
                self.system_prompt = ""

            logging.info("Initialized %d tools from MCP server", len(self.tools or []))
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.logger.error("Failed to initialize MCP tools: %s", exc)
            raise

    async def _get_system_prompt(self) -> str:
        """Get system prompt from MCP server."""
        try:
            init_request = create_mcp_init_request()
            response = requests.post(self.server_url, json=init_request, headers=DEFAULT_JSON_HEADERS, timeout=10)
            if response.status_code == 200:
                response_data = parse_mcp_response(response.text)
                if isinstance(response_data, dict) and "result" in response_data:
                    return response_data["result"].get("instructions", "")
            return ""
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.logger.warning("Failed to get system prompt: %s", exc)
            return ""

    def _record_tool_call(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> None:
        """Record a tool call in a deepeval-compatible structure."""
        if len(self._called_tools) > 0 and self._called_tools[-1].name == tool_name:
            return
        args = arguments or {}
        self._called_tools.append(tool_call_record(tool_name, args))

    def _wrap_one_tool(self, tool: Union[BaseTool, Callable]) -> Union[BaseTool, Callable]:
        """Monkey-patch a tool to record invocations while preserving behavior."""
        try:
            tool_name: str
            if hasattr(tool, "metadata") and getattr(tool, "metadata") is not None:
                tool_name = str(getattr(tool.metadata, "name", "unknown"))
            else:
                name_attr = getattr(tool, "name", None)
                tool_name = (
                    str(name_attr) if name_attr is not None else (f"unknown class:{tool.__class__.__name__} {tool}")
                )

            if hasattr(tool, "acall") and asyncio.iscoroutinefunction(getattr(tool, "acall")):
                original_acall = getattr(tool, "acall")

                async def wrapped_acall(*args: Any, **kwargs: Any) -> Any:  # type: ignore
                    self._record_tool_call(tool_name, kwargs)
                    return await original_acall(*args, **kwargs)

                setattr(tool, "acall", wrapped_acall)
                return tool

            if hasattr(tool, "__call__") and asyncio.iscoroutinefunction(getattr(tool, "__call__")):
                original_call = getattr(tool, "__call__")

                async def wrapped_call(*args: Any, **kwargs: Any) -> Any:  # type: ignore
                    self._record_tool_call(tool_name, kwargs)
                    return await original_call(*args, **kwargs)

                setattr(tool, "__call__", wrapped_call)  # type: ignore
                return tool

            if hasattr(tool, "call") and callable(getattr(tool, "call")):
                original_sync_call = getattr(tool, "call")

                async def wrapped_sync(*args: Any, **kwargs: Any) -> Any:
                    self._record_tool_call(tool_name, kwargs)
                    return await asyncio.to_thread(original_sync_call, *args, **kwargs)

                setattr(tool, "acall", wrapped_sync)
                return tool

            if callable(tool):
                original_callable = tool

                async def wrapped_callable(*args: Any, **kwargs: Any) -> Any:
                    self._record_tool_call(tool_name, kwargs)
                    if asyncio.iscoroutinefunction(original_callable):
                        return await original_callable(*args, **kwargs)
                    return await asyncio.to_thread(original_callable, *args, **kwargs)

                setattr(tool, "acall", wrapped_callable)
                return tool

            return tool
        except Exception:  # pylint: disable=broad-exception-caught
            return tool

    def _wrap_tools_for_recording(self) -> None:
        if not self.tools:
            return
        wrapped: List[Union[BaseTool, Callable]] = []
        for step_tool in self.tools:
            wrapped.append(self._wrap_one_tool(step_tool))
        self.tools = wrapped

    async def _setup_agent(self):
        """Setup LlamaIndex agent with MCP tools and optional verbose logging."""
        self._called_tools = []
        self._step_names = []

        self._wrap_tools_for_recording()

        self.agent = FunctionAgent(
            name="MCP Agent",
            description="Agent with MCP tools",
            system_prompt=self.system_prompt,
            llm=self.llama_llm,
            tools=self.tools,
            streaming=False,
            allow_parallel_tool_calls=False,
        )
        self.context = Context(self.agent)

        self.logger.info("📝 Initialized workflow with event streaming for step logging")

    async def execute_with_reasoning(
        self,
        user_msg: str,
        chat_history: Optional[List[ChatMessage]] = None,
        max_iterations: int = 10,
    ) -> Tuple[str, List[Dict[str, Any]], List[Any], List[ChatMessage]]:
        """Execute agent, record tool calls and steps, return response and artifacts."""
        if chat_history is None:
            chat_history = []
        # FunctionAgent prepends system_prompt in setup_agent; do not duplicate it here.
        chat_history = [message for message in chat_history if message.role != "system"]
        if chat_history:
            chat_history = _compact_chat_history_for_followup(chat_history)
            if _is_paging_followup(user_msg, chat_history):
                # Drop prior assistant text (often auth-error instructions) so the model
                # calls get_blueprints for the next page instead of continuing that narrative.
                user_msg = _paging_followup_user_message(user_msg)
                chat_history = []
            elif "pro" in self.model_id.lower():
                # Gemini Pro rejects multi-turn chat replay with tools; embed context instead.
                user_msg, chat_history = _embed_chat_history_in_user_message(user_msg, chat_history)

        if not self.agent or self.llama_llm is None:
            raise ValueError("Agent not initialized")

        def _history_summary(messages: List[ChatMessage]) -> dict:
            summary: List[dict] = []
            for message in messages[:20]:
                content = message.content
                if isinstance(content, str):
                    content_kind = "str"
                    content_len = len(content)
                elif isinstance(content, list):
                    content_kind = "list"
                    content_len = len(content)
                    block_types = [
                        block.get("type") if isinstance(block, dict) else type(block).__name__ for block in content[:8]
                    ]
                    summary.append(
                        {
                            "role": message.role,
                            "content_kind": content_kind,
                            "content_len": content_len,
                            "block_types": block_types,
                        }
                    )
                    continue
                else:
                    content_kind = type(content).__name__
                    content_len = 0
                entry: dict = {
                    "role": message.role,
                    "content_kind": content_kind,
                    "content_len": content_len,
                }
                extra = getattr(message, "additional_kwargs", None) or {}
                if extra:
                    entry["additional_keys"] = list(extra.keys())
                    if "tool_calls" in extra:
                        entry["tool_calls_count"] = len(extra["tool_calls"])
                summary.append(entry)
            return {"count": len(messages), "messages": summary}

        self.logger.info("🎬 Starting workflow execution...")
        self.logger.info("📝 User message: %s", user_msg)

        response: Any = None
        self.context = Context(self.agent)
        for attempt in range(2):
            # Per-turn isolation: stale workflow context breaks follow-up turns on some gateways.
            self._called_tools = []
            self._step_names = []

            handler = self.agent.run(
                user_msg=user_msg,
                ctx=self.context,
                chat_history=chat_history,
                max_iterations=max_iterations,
            )

            async def _stream_events() -> None:
                async for ev in handler.stream_events():
                    ev_name = ev.__class__.__name__
                    self._step_names.append(ev_name)
                    if self.logger and ev_name not in ["AgentStream"]:
                        data_str = f"{ev}"
                        if len(data_str) > 2000:
                            data_str = data_str[:1000] + "\n<… abbreviated log …>\n" + data_str[-1000:]
                        self.logger.debug("📡 Event %s: %s", ev_name, data_str)

            stream_task = asyncio.create_task(_stream_events())
            try:
                response = await handler
            except Exception:
                raise
            finally:
                try:
                    await asyncio.wait_for(stream_task, timeout=0.5)
                except asyncio.TimeoutError:
                    stream_task.cancel()

            attempt_text = _assistant_text_from_handler_response(response)
            if attempt_text.strip() or self._called_tools:
                break
            if attempt == 0:
                self.logger.warning(
                    "Empty agent response with no tool calls for model %s; retrying once",
                    self.model_id,
                )

        reasoning_steps: List[Dict[str, Any]] = [
            {"step_number": idx + 1, "step_type": "event", "content": name} for idx, name in enumerate(self._step_names)
        ]

        assistant_text = _assistant_text_from_handler_response(response)
        agent_tool_calls = len(response.tool_calls) if isinstance(response, AgentOutput) and response.tool_calls else 0
        memory = await self.context.store.get("memory")
        if memory is not None:
            updated_history = await memory.aget()
        else:
            updated_history = chat_history + [ChatMessage(role="user", content=user_msg)]
            updated_history.append(ChatMessage(role="assistant", content=assistant_text))

        tools_called: List[Any] = list(self._called_tools)

        self.logger.info("🔍 Agent response: %s", assistant_text)
        if tools_called:
            self.logger.info("🔧 Tools called (%s calls): %s", agent_tool_calls, [t.name for t in tools_called])
        else:
            self.logger.info("🔧 No tools called")

        return assistant_text, reasoning_steps, tools_called, updated_history

    def get_all_checkpoints(self) -> Dict[str, List[Any]]:  # pylint: disable=too-few-public-methods
        """No longer uses checkpoints; returns empty mapping for compatibility."""
        return {}

    def get_checkpoints_for_run(self, run_id: str) -> List[Any]:  # pylint: disable=unused-argument
        """No longer uses checkpoints; returns empty list for compatibility."""
        return []


__all__ = ["MCPAgentWrapper"]
