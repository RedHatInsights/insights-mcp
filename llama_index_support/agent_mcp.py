"""LlamaIndex MCP agent used by behavioral integration tests."""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import requests
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.base.llms.types import LLMMetadata
from llama_index.core.llms import ChatMessage
from llama_index.core.tools import BaseTool
from llama_index.core.workflow import Context
from llama_index.llms.openai import OpenAI
from llama_index.tools.mcp import BasicMCPClient, McpToolSpec

from deepeval_support.tool_calls import tool_call_record
from instrumentation_tests.mcp_jsonrpc import (
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

        self._called_tools: List[Any] = []
        self._step_names: List[str] = []

        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        self.llama_llm = CustomLlamaIndexLLM(
            api_url=api_url,
            model_id=model_id,
            api_key=api_key,
            system_prompt="You are a helpful assistant that can use tools to answer questions and perform tasks.",
        )
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        if verbose_logger:
            self.logger = verbose_logger

        asyncio.run(self._initialize())

    async def _initialize(self):
        """Initialize MCP session and get available tools."""
        await self._init_mcp_tools()
        await self._setup_agent()

    async def _init_mcp_tools(self):
        """Initialize MCP tools using LlamaIndex MCP support."""
        try:
            if self.server_url == "stdio":
                mcp_client = BasicMCPClient("python", args=["-m", "insights_mcp.server", "stdio"])
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
        if chat_history is None or len(chat_history) == 0:
            if self.system_prompt:
                chat_history = [ChatMessage(role="system", content=self.system_prompt)]
            else:
                chat_history = []

        if not self.agent or not self.context:
            raise ValueError("Agent or context not initialized")

        self.logger.info("🎬 Starting workflow execution...")
        self.logger.info("📝 User message: %s", user_msg)

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
        finally:
            try:
                await asyncio.wait_for(stream_task, timeout=0.5)
            except asyncio.TimeoutError:
                stream_task.cancel()

        reasoning_steps: List[Dict[str, Any]] = [
            {"step_number": idx + 1, "step_type": "event", "content": name} for idx, name in enumerate(self._step_names)
        ]

        updated_history = chat_history + [ChatMessage(role="user", content=user_msg)]
        updated_history.append(ChatMessage(role="assistant", content=str(response)))

        tools_called: List[Any] = list(self._called_tools)

        self.logger.info("🔍 Agent response: %s", response)
        if tools_called:
            self.logger.info("🔧 Tools called: %s", [t.name for t in tools_called])
        else:
            self.logger.info("🔧 No tools called")

        return str(response), reasoning_steps, tools_called, updated_history

    def get_all_checkpoints(self) -> Dict[str, List[Any]]:  # pylint: disable=too-few-public-methods
        """No longer uses checkpoints; returns empty mapping for compatibility."""
        return {}

    def get_checkpoints_for_run(self, run_id: str) -> List[Any]:  # pylint: disable=unused-argument
        """No longer uses checkpoints; returns empty list for compatibility."""
        return []


# pylint: disable=too-few-public-methods,too-many-ancestors
class CustomLlamaIndexLLM(OpenAI):
    """Custom LlamaIndex LLM that wraps vLLM with OpenAI-compatible API."""

    def __init__(self, api_url: str, model_id: str, api_key: str, system_prompt: str = "", **kwargs):
        temperature = kwargs.pop("temperature", 0.1)
        merged_additional_kwargs = dict(kwargs.pop("additional_kwargs", None) or {})
        # OpenAI-compat APIs (including some Gemini gateways) stream multiple tool_calls; collapsing
        # them can merge names/ids — request at most one tool call per assistant turn unless overridden.
        merged_additional_kwargs.setdefault("parallel_tool_calls", False)
        super().__init__(
            model=model_id,
            api_key=api_key,
            api_base=api_url,
            temperature=temperature,
            additional_kwargs=merged_additional_kwargs,
            **kwargs,
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


__all__ = ["CustomLlamaIndexLLM", "MCPAgentWrapper"]
