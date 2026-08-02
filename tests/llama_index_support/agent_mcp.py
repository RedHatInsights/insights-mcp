"""LlamaIndex MCP agent used by behavioral integration tests."""

import asyncio
import logging
import uuid
from typing import Any, Optional, Sequence, cast

import httpx
from llama_index.core.agent.workflow.function_agent import FunctionAgent
from llama_index.core.agent.workflow.workflow_events import AgentOutput
from llama_index.core.base.llms.types import ChatResponse, ToolCallBlock
from llama_index.core.llms import ChatMessage
from llama_index.core.llms.function_calling import FunctionCallingLLM
from llama_index.core.memory import Memory
from llama_index.core.storage.chat_store.sql import MessageStatus
from llama_index.core.tools import AsyncBaseTool, BaseTool
from llama_index.core.workflow import Context
from llama_index.llms.openai_like import OpenAILike
from llama_index.tools.mcp import BasicMCPClient, McpToolSpec
from mcp.shared._httpx_utils import create_mcp_http_client

from instrumentation_tests.mcp_jsonrpc import (
    fetch_mcp_instructions_http,
    fetch_mcp_instructions_stdio,
)
from tests.deepeval_support.tracing import WorkflowToolCallCollector, tools_called_from_agent_run

# Align with OpenAILike context_window in initialize(). Large enough for tool results + follow-up turns.
_LLM_CONTEXT_TOKEN_LIMIT = 16384

_MCP_INSTRUCTIONS_HEADER = "## MCP server instructions"
_USER_REQUEST_HEADER = "## User request"

_STDIO_MCP_COMMAND = "python"
_STDIO_MCP_ARGS = ["-m", "insights_mcp.server", "stdio"]


def format_user_message_with_mcp_instructions(user_msg: str, mcp_instructions: str) -> str:
    """Prepend MCP initialize instructions to the user turn (Granite-safe vs system_prompt)."""
    if not mcp_instructions.strip():
        return user_msg
    return f"{_MCP_INSTRUCTIONS_HEADER}\n{mcp_instructions.strip()}\n\n{_USER_REQUEST_HEADER}\n{user_msg}"


def _chat_message_text(message: ChatMessage) -> str:
    """Extract display text from a ChatMessage (content string or text blocks)."""
    content = message.content
    if isinstance(content, str) and content:
        return content
    block_texts: list[str] = []
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


def _chat_history_without_system(messages: list[ChatMessage]) -> list[ChatMessage]:
    """Drop system messages; MCP instructions are injected on the user turn instead."""
    return [message for message in messages if message.role != "system"]


def _preserve_tool_call_metadata(messages: list[ChatMessage]) -> list[ChatMessage]:
    """Ensure provider-specific tool call metadata survives message serialization.

    llama-index reconstructs tool calls from ToolCallBlocks, dropping any extra fields
    the provider included (e.g. Gemini thought_signature). When the original raw tool_calls
    are available in additional_kwargs, remove the ToolCallBlocks so the serializer uses the
    complete originals instead.
    """
    patched: list[ChatMessage] = []
    for msg in messages:
        if msg.role == "assistant" and "tool_calls" in msg.additional_kwargs:
            blocks = [b for b in msg.blocks if not isinstance(b, ToolCallBlock)]
            msg = ChatMessage(role=msg.role, blocks=blocks, additional_kwargs=msg.additional_kwargs)
        patched.append(msg)
    return patched


class ToolRequiredFunctionAgent(FunctionAgent):
    """FunctionAgent that sets OpenAI ``tool_choice: required`` before the first tool result.

    Mistral and similar gateways often return prose instead of ``tool_calls`` once roughly
    seven or more tools are registered; ``tool_required`` is the reliable OpenAI fix.
    Applied for all matrix models in this harness, not only Mistral.
    """

    async def _get_response(
        self,
        current_llm_input: list[ChatMessage],
        tools: Sequence[AsyncBaseTool],
    ) -> ChatResponse:
        # Require a tool call only before any tool output is in context; later turns need room for history.
        tool_required = not any(message.role == "tool" for message in current_llm_input)
        chat_kwargs: dict[str, Any] = {
            "chat_history": _preserve_tool_call_metadata(current_llm_input),
            "allow_parallel_tool_calls": self.allow_parallel_tool_calls,
            "tools": tools,
            "tool_required": tool_required,
        }
        if self.initial_tool_choice is not None and current_llm_input[-1].role == "user":
            chat_kwargs["tool_choice"] = self.initial_tool_choice
        function_calling_llm = cast(FunctionCallingLLM, self.llm)
        return await function_calling_llm.achat_with_tools(**chat_kwargs)


class MCPAgentWrapper:  # pylint: disable=too-many-instance-attributes
    """MCP agent harness for behavioral LLM tests.

    Multi-turn history uses LlamaIndex ``Memory`` (``agent.run(..., memory=...)``).
    Tool calls are recorded from workflow stream events (``tests.deepeval_support.tracing``).
    """

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def __init__(
        self,
        server_url: str,
        api_url: str,
        model_id: str,
        api_key: str,
        verbose_logger: Optional[logging.Logger] = None,
        mcp_http_headers: Optional[dict[str, str]] = None,
    ):  # pylint: disable=too-many-instance-attributes
        self.server_url = server_url
        self.mcp_http_headers = mcp_http_headers
        self.api_url = api_url
        self.model_id = model_id
        self.api_key = api_key
        self.tools: Optional[list[BaseTool]] = []
        self.mcp_instructions = ""
        self.agent: Optional[FunctionAgent] = None
        self.context: Optional[Context] = None

        self._session_id = str(uuid.uuid4())
        self._memory: Optional[Memory] = None
        self._step_names: list[str] = []
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
            context_window=_LLM_CONTEXT_TOKEN_LIMIT,
            max_tokens=1024,
            is_chat_model=True,
            is_function_calling_model=True,
            # Some OpenAI-compatible gateways (e.g. Mistral) reject strict JSON-schema tool mode.
            strict=False,
            async_http_client=self._llm_http_client,
        )
        self._memory = Memory.from_defaults(
            session_id=self._session_id,
            token_limit=_LLM_CONTEXT_TOKEN_LIMIT,
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

    async def get_archived_messages(self) -> list[ChatMessage]:
        """Return messages archived by Memory waterfall (empty if under token_limit)."""
        if self._memory is None:
            raise ValueError("Agent not initialized")
        return await self._memory.aget_all(status=MessageStatus.ARCHIVED)

    async def get_active_memory_token_estimate(self) -> int:
        """Estimate tokens in the active Memory queue (same logic as Memory waterfall)."""
        if self._memory is None:
            raise ValueError("Agent not initialized")
        active_messages = await self._memory.aget_all(status=MessageStatus.ACTIVE)
        return sum(self._memory._estimate_token_count(message) for message in active_messages)

    async def _init_mcp_tools(self):
        """Initialize MCP tools using LlamaIndex MCP support."""
        try:
            if self.server_url == "stdio":
                mcp_client = BasicMCPClient(_STDIO_MCP_COMMAND, args=_STDIO_MCP_ARGS)
            else:
                mcp_http_client = create_mcp_http_client(headers=self.mcp_http_headers)
                mcp_client = BasicMCPClient(self.server_url, http_client=mcp_http_client)
            self._mcp_client = mcp_client
            mcp_tool_spec = McpToolSpec(client=mcp_client)
            self.tools = await mcp_tool_spec.to_tool_list_async()
            self.mcp_instructions = await self._fetch_mcp_instructions()

            if self.mcp_instructions:
                self.logger.info(
                    "Loaded MCP initialize instructions (%d chars); delivering via user message",
                    len(self.mcp_instructions),
                )
            logging.info("Initialized %d tools from MCP server", len(self.tools or []))
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.logger.error("Failed to initialize MCP tools: %s", exc)
            raise

    async def _fetch_mcp_instructions(self) -> str:
        """Load MCP ``initialize`` instructions for HTTP, SSE, or stdio transports."""
        try:
            if self.server_url == "stdio":
                return await fetch_mcp_instructions_stdio(_STDIO_MCP_COMMAND, _STDIO_MCP_ARGS)
            if self.server_url.startswith("http"):
                return fetch_mcp_instructions_http(self.server_url, headers=self.mcp_http_headers)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.logger.warning("Failed to fetch MCP instructions: %s", exc)
        return ""

    async def _setup_agent(self):
        """Setup LlamaIndex agent with MCP tools and optional verbose logging."""
        self._step_names = []

        self.agent = ToolRequiredFunctionAgent(
            name="MCP Agent",
            description="Agent with MCP tools",
            system_prompt=None,
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
        chat_history: Optional[list[ChatMessage]] = None,
        max_iterations: int = 10,
    ) -> tuple[str, list[dict[str, Any]], list[Any], list[ChatMessage]]:
        """Execute agent, record tool calls and steps, return response and artifacts."""
        if not self.agent or self.llama_llm is None or self._memory is None:
            raise ValueError("Agent not initialized")

        prior_history = _chat_history_without_system(chat_history or [])
        await self._memory.aset(prior_history)

        agent_user_msg = user_msg
        if self.mcp_instructions and not prior_history:
            agent_user_msg = format_user_message_with_mcp_instructions(user_msg, self.mcp_instructions)

        self.logger.info("🎬 Starting workflow execution...")
        self.logger.info("📝 User message: %s", user_msg)

        response: Any = None
        tool_collector = WorkflowToolCallCollector()
        self.context = Context(self.agent)
        for attempt in range(2):
            tool_collector.clear()
            self._step_names = []

            handler = self.agent.run(
                user_msg=agent_user_msg,
                ctx=self.context,
                memory=self._memory,
                max_iterations=max_iterations,
            )

            async def _stream_events() -> None:
                async for ev in handler.stream_events():
                    tool_collector.consume_event(ev)
                    ev_name = ev.__class__.__name__
                    self._step_names.append(ev_name)
                    if self.logger and ev_name not in ["AgentStream"]:
                        data_str = f"{ev}"
                        if len(data_str) > 2000:
                            data_str = data_str[:1000] + "\n<… abbreviated log …>\n" + data_str[-1000:]
                        if ev_name == "ToolCall":
                            log_function = self.logger.info
                        else:
                            log_function = self.logger.debug
                        log_function("📡 Event %s: %s", ev_name, data_str)

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
            if attempt_text.strip() or tool_collector.as_list():
                break
            if attempt == 0:
                self.logger.warning(
                    "Empty agent response with no tool calls for model %s; retrying once",
                    self.model_id,
                )

        reasoning_steps: list[dict[str, Any]] = [
            {"step_number": idx + 1, "step_type": "event", "content": name} for idx, name in enumerate(self._step_names)
        ]

        assistant_text = _assistant_text_from_handler_response(response)
        agent_tool_calls = len(response.tool_calls) if isinstance(response, AgentOutput) and response.tool_calls else 0
        updated_history = await self._memory.aget()

        tools_called = tools_called_from_agent_run(response, workflow_collector=tool_collector)

        self.logger.info("🔍 Agent response: %s", assistant_text)
        if tools_called:
            self.logger.info("🔧 Tools called (%s calls): %s", agent_tool_calls, [t.name for t in tools_called])
        else:
            self.logger.info("🔧 No tools called")

        return assistant_text, reasoning_steps, tools_called, updated_history


__all__ = ["MCPAgentWrapper", "format_user_message_with_mcp_instructions"]
