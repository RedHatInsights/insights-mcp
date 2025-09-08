"""Enhanced MCP Agent implementation focused on extracting called tools and steps.

This implementation removes reliance on deprecated WorkflowCheckpointer and instead:
- Wraps tools to record invocations for validation in tests
- Streams workflow events to optionally log step progression
- Returns called tools for assertions and minimal reasoning steps for logs
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import requests
from deepeval.test_case import ToolCall
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.base.llms.types import LLMMetadata
from llama_index.core.llms import ChatMessage
from llama_index.core.tools import BaseTool
from llama_index.core.workflow import Context
from llama_index.llms.openai import OpenAI
from llama_index.tools.mcp import BasicMCPClient, McpToolSpec

from .utils import (
    DEFAULT_JSON_HEADERS,
    create_mcp_init_request,
    parse_mcp_response,
)


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

        # Recorded data
        self._called_tools: List[ToolCall] = []
        self._step_names: List[str] = []

        # Set up logging for debugging
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Initialize LlamaIndex LLM
        self.llama_llm = CustomLlamaIndexLLM(
            api_url=api_url,
            model_id=model_id,
            api_key=api_key,
            system_prompt="You are a helpful assistant that can use tools to answer questions and perform tasks.",
        )
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        if verbose_logger:
            self.logger = verbose_logger

        # Run async initialization
        asyncio.run(self._initialize())

    async def _initialize(self):
        """Initialize MCP session and get available tools."""
        await self._init_mcp_tools()
        await self._setup_agent()

    async def _init_mcp_tools(self):
        """Initialize MCP tools using LlamaIndex MCP support."""
        try:
            # Support stdio transport by launching the server as a subprocess
            if self.server_url == "stdio":
                mcp_client = BasicMCPClient("python", args=["-m", "insights_mcp.server", "stdio"])
                # For stdio we cannot fetch HTTP instructions; leave system prompt empty
                fetch_system_prompt = False
            else:
                mcp_client = BasicMCPClient(self.server_url)
                fetch_system_prompt = self.server_url.startswith("http")

            mcp_tool_spec = McpToolSpec(client=mcp_client)
            self.tools = await mcp_tool_spec.to_tool_list_async()

            if fetch_system_prompt:
                self.system_prompt = await self._get_system_prompt()
            else:
                self.system_prompt = ""

            logging.info("Initialized %d tools from MCP server", len(self.tools or []))
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Failed to initialize MCP tools: %s", e)
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
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.warning("Failed to get system prompt: %s", e)
            return ""

    def _record_tool_call(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> None:
        """Record a tool call in a deepeval-compatible structure."""
        if len(self._called_tools) > 0 and self._called_tools[-1].name == tool_name:
            return
        args = arguments or {}
        self._called_tools.append(ToolCall(name=tool_name, input_parameters=args))

    def _wrap_one_tool(self, tool: Union[BaseTool, Callable]) -> Union[BaseTool, Callable]:
        """Monkey-patch a tool to record invocations while preserving behavior."""
        try:
            # Resolve tool name robustly and ensure it's str for typing
            tool_name: str
            if hasattr(tool, "metadata") and getattr(tool, "metadata") is not None:
                tool_name = str(getattr(tool.metadata, "name", "unknown"))
            else:
                name_attr = getattr(tool, "name", None)
                tool_name = (
                    str(name_attr) if name_attr is not None else (f"unknown class:{tool.__class__.__name__} {tool}")
                )

            # Prefer async path if available
            if hasattr(tool, "acall") and asyncio.iscoroutinefunction(getattr(tool, "acall")):
                original_acall = getattr(tool, "acall")

                async def wrapped_acall(*args: Any, **kwargs: Any) -> Any:  # type: ignore
                    self._record_tool_call(tool_name, kwargs)
                    return await original_acall(*args, **kwargs)

                setattr(tool, "acall", wrapped_acall)
                return tool

            # Some BaseTool implementations expose __call__ as async
            if hasattr(tool, "__call__") and asyncio.iscoroutinefunction(getattr(tool, "__call__")):
                original_call = getattr(tool, "__call__")

                async def wrapped_call(*args: Any, **kwargs: Any) -> Any:  # type: ignore
                    self._record_tool_call(tool_name, kwargs)
                    return await original_call(*args, **kwargs)

                setattr(tool, "__call__", wrapped_call)  # type: ignore
                return tool

            # Fallback: sync call path
            if hasattr(tool, "call") and callable(getattr(tool, "call")):
                original_sync_call = getattr(tool, "call")

                async def wrapped_sync(*args: Any, **kwargs: Any) -> Any:
                    self._record_tool_call(tool_name, kwargs)
                    return await asyncio.to_thread(original_sync_call, *args, **kwargs)

                # Prefer to expose async interface to agent
                setattr(tool, "acall", wrapped_sync)
                return tool

            if callable(tool):
                original_callable = tool

                async def wrapped_callable(*args: Any, **kwargs: Any) -> Any:
                    self._record_tool_call(tool_name, kwargs)
                    if asyncio.iscoroutinefunction(original_callable):
                        return await original_callable(*args, **kwargs)
                    return await asyncio.to_thread(original_callable, *args, **kwargs)

                # Expose as async entrypoint commonly used by tools
                setattr(tool, "acall", wrapped_callable)
                return tool

            return tool
        except Exception:  # pylint: disable=broad-exception-caught
            # If wrapping fails, return original tool unmodified
            return tool

    def _wrap_tools_for_recording(self) -> None:
        if not self.tools:
            return
        wrapped: List[Union[BaseTool, Callable]] = []
        for t in self.tools:
            wrapped.append(self._wrap_one_tool(t))
        self.tools = wrapped

    async def _setup_agent(self):
        """Setup LlamaIndex agent with MCP tools and optional verbose logging."""
        # Reset recordings for a new session
        self._called_tools = []
        self._step_names = []

        # Wrap tools first so the agent uses the wrapped versions
        self._wrap_tools_for_recording()

        self.agent = FunctionAgent(
            name="MCP Agent",
            description="Agent with MCP tools",
            system_prompt=self.system_prompt,
            llm=self.llama_llm,
            tools=self.tools,
        )
        self.context = Context(self.agent)

        self.logger.info("📝 Initialized workflow with event streaming for step logging")

    async def execute_with_reasoning(  # pylint: disable=too-many-locals
        self,
        user_msg: str,
        chat_history: Optional[List[ChatMessage]] = None,
        max_iterations: int = 10,
    ) -> Tuple[str, List[Dict[str, Any]], List[Any], List[ChatMessage]]:  # pylint: disable=too-many-locals,too-many-arguments
        """Execute agent, record tool calls and steps, return response and artifacts."""
        if chat_history is None or len(chat_history) == 0:
            # ensure system prompt is included in chat history
            if self.system_prompt:
                chat_history = [ChatMessage(role="system", content=self.system_prompt)]
            else:
                chat_history = []

        if not self.agent or not self.context:
            raise ValueError("Agent or context not initialized")

        # Stream events for optional step logging while the workflow runs
        self.logger.info("🎬 Starting workflow execution...")
        self.logger.info("📝 User message: %s", user_msg)

        handler = self.agent.run(
            user_msg=user_msg,
            ctx=self.context,
            chat_history=chat_history,
            max_iterations=max_iterations,
        )

        # Consume events to capture step progression
        async def _stream_events() -> None:
            async for ev in handler.stream_events():
                ev_name = ev.__class__.__name__
                self._step_names.append(ev_name)
                if self.logger and ev_name not in ["AgentStream"]:
                    data = f"{ev}"
                    if len(data) > 2000:
                        data = data[:1000] + "\n<… abbreviated log …>\n" + data[-1000:]
                    self.logger.debug("📡 Event %s: %s", ev_name, data)

        # Run streaming in background while awaiting result
        stream_task = asyncio.create_task(_stream_events())
        try:
            response = await handler
        finally:
            # Ensure streaming task cleaned up
            try:
                await asyncio.wait_for(stream_task, timeout=0.5)
            except asyncio.TimeoutError:
                stream_task.cancel()

        # Build minimal reasoning steps from recorded step names
        reasoning_steps: List[Dict[str, Any]] = [
            {"step_number": i + 1, "step_type": "event", "content": name} for i, name in enumerate(self._step_names)
        ]

        # Build updated chat history
        updated_history = chat_history + [ChatMessage(role="user", content=user_msg)]
        updated_history.append(ChatMessage(role="assistant", content=str(response)))

        # Return called tools as recorded
        tools_called: List[Any] = list(self._called_tools)

        self.logger.info("🔍 Agent response: %s", response)
        if tools_called:
            self.logger.info("🔧 Tools called: %s", [t.name for t in tools_called])
        else:
            self.logger.info("🔧 No tools called")

        return str(response), reasoning_steps, tools_called, updated_history

    # Backwards-compat small helpers used by tests elsewhere
    def get_all_checkpoints(self) -> Dict[str, List[Any]]:  # pylint: disable=too-few-public-methods
        """No longer uses checkpoints; returns empty mapping for compatibility."""
        return {}

    def get_checkpoints_for_run(self, run_id: str) -> List[Any]:  # pylint: disable=unused-argument
        """No longer uses checkpoints; returns empty list for compatibility."""
        return []


# Reuse the CustomLlamaIndexLLM from the original implementation
# pylint: disable=too-few-public-methods,too-many-ancestors
class CustomLlamaIndexLLM(OpenAI):
    """Custom LlamaIndex LLM that wraps vLLM with OpenAI-compatible API."""

    def __init__(self, api_url: str, model_id: str, api_key: str, system_prompt: str = "", **kwargs):
        super().__init__(
            model=model_id, api_key=api_key, api_base=api_url, temperature=kwargs.get("temperature", 0.1), **kwargs
        )
        self._custom_model_id = model_id
        self._system_prompt = system_prompt

    @property
    def metadata(self):
        """Override metadata to provide context window for custom models."""
        return LLMMetadata(
            context_window=8192,
            num_output=2048,
            is_chat_model=True,
            is_function_calling_model=True,
            model_name=self._custom_model_id,
        )
