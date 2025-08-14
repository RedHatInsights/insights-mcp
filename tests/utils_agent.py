"""Enhanced MCP Agent implementation with WorkflowCheckpointer.

This implementation provides comprehensive agent reasoning capture, enhanced failure handling,
and tool call extraction using LlamaIndex's native WorkflowCheckpointer for reliable
debugging and testing of MCP server interactions.

Features:
- Full reasoning step extraction from workflow checkpoints
- Enhanced failure handling with partial progress reporting
- Tool call tracking and analysis
- Real agent output parsing from checkpoint events
- Robust error reporting with actionable debugging suggestions
"""

import asyncio
import logging
from typing import Awaitable, Callable, Dict, List, Any, Tuple, Optional, Union

import requests
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.core.workflow import Context
from llama_index.core.workflow.checkpointer import WorkflowCheckpointer
from llama_index.llms.openai import OpenAI
from llama_index.core.llms import ChatMessage
from llama_index.tools.mcp import BasicMCPClient, McpToolSpec
from llama_index.core.base.llms.types import LLMMetadata
from llama_index.core.tools import BaseTool
from workflows.events import Event
from workflows.checkpointer import CheckpointCallback
from deepeval.test_case import ToolCall

from .utils import (
    DEFAULT_JSON_HEADERS,
    create_mcp_init_request,
    parse_mcp_response,
)


class VerboseStartCheckpointCallback(CheckpointCallback):  # pylint: disable=too-few-public-methods
    """Custom checkpoint callback that logs step starts to verbose_logger."""

    def __init__(self, verbose_logger: logging.Logger, *args, **kwargs):  # pylint: disable=too-many-arguments
        super().__init__(*args, **kwargs)
        self.verbose_logger = verbose_logger

    def __call__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        run_id: str,
        last_completed_step: str | None,
        input_ev: Event | None,
        output_ev: Event | None,
        ctx: "Context",
    ) -> Awaitable[None]:
        """Called when a workflow step starts - log it live."""
        return self.on_step_start(last_completed_step or "unknown_step", {}, input_ev, output_ev)

    async def on_step_start(
        self,
        step_name: str,
        context: Dict[str, Any],  # pylint: disable=unused-argument
        input_ev: Event | None,
        output_ev: Event | None,
    ):  # pylint: disable=unused-argument
        """Called when a workflow step starts - log it live."""

        context_str = "no details"

        if input_ev:
            context_str = f"{input_ev.__class__.__name__} {input_ev}"

        output_str = f"🚀 {step_name} ({context_str})"

        if len(output_str) > 2000:
            self.verbose_logger.debug(output_str[:1000] + "\n<… abbreviated log …>\n" + output_str[-1000:])
        else:
            self.verbose_logger.debug(output_str)


class VerboseWorkflowCheckpointer(WorkflowCheckpointer):
    """Custom WorkflowCheckpointer that provides live step start logging."""

    def __init__(self, workflow, verbose_logger: logging.Logger, *args, **kwargs):  # pylint: disable=too-many-arguments
        super().__init__(workflow, *args, **kwargs)
        self.verbose_logger = verbose_logger

    def new_checkpoint_callback_for_run(self) -> CheckpointCallback:
        """Override to return our verbose start callback."""
        return VerboseStartCheckpointCallback(verbose_logger=self.verbose_logger)


class MCPAgentWrapper:  # pylint: disable=too-many-instance-attributes
    """Enhanced MCP agent wrapper with comprehensive reasoning capture and failure handling.

    This implementation leverages LlamaIndex's WorkflowCheckpointer to provide detailed
    visibility into agent reasoning, tool execution, and failure scenarios. It captures
    real agent outputs, tool calls, and intermediate reasoning steps for debugging and testing.
    """

    def __init__(self, server_url: str, api_url: str, model_id: str, api_key: str):  # pylint: disable=too-many-instance-attributes
        self.server_url = server_url
        self.api_url = api_url
        self.model_id = model_id
        self.api_key = api_key
        self.tools: Optional[List[Union[BaseTool, Callable]]] = []
        self.system_prompt = ""
        self.agent: Optional[FunctionAgent] = None
        self.context: Optional[Context] = None
        self.checkpointer: Optional[WorkflowCheckpointer] = None

        # Set up logging for debugging
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Initialize LlamaIndex LLM
        self.llama_llm = CustomLlamaIndexLLM(api_url=api_url, model_id=model_id, api_key=api_key)

        # Run async initialization
        asyncio.run(self._initialize())

    async def _initialize(self):
        """Initialize MCP session and get available tools."""
        await self._init_mcp_tools()
        await self._setup_agent()

    async def _init_mcp_tools(self):
        """Initialize MCP tools using LlamaIndex MCP support."""
        try:
            mcp_client = BasicMCPClient(self.server_url)
            mcp_tool_spec = McpToolSpec(client=mcp_client)
            self.tools = await mcp_tool_spec.to_tool_list_async()
            self.system_prompt = await self._get_system_prompt()
            logging.info("Initialized %d tools from MCP server", len(self.tools))
        except Exception as e:  # pylint: disable=broad-exception-caught
            logging.error("Failed to initialize MCP tools: %s", e)
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
            logging.warning("Failed to get system prompt: %s", e)
            return ""

    async def _setup_agent(self, verbose_logger: Optional[logging.Logger] = None):
        """Setup LlamaIndex agent with MCP tools and optional verbose checkpointer."""
        self.agent = FunctionAgent(
            name="MCP Agent",
            description="Agent with MCP tools",
            llm=self.llama_llm,
            tools=self.tools,
        )
        self.context = Context(self.agent)

        # Use verbose checkpointer if logger provided, otherwise standard checkpointer
        if verbose_logger:
            self.checkpointer = VerboseWorkflowCheckpointer(workflow=self.agent, verbose_logger=verbose_logger)
            verbose_logger.info("📝 Initialized workflow with live step start logging")
        else:
            self.checkpointer = WorkflowCheckpointer(workflow=self.agent)

    def _extract_reasoning_from_checkpoints(self, run_id: str) -> List[Dict[str, Any]]:  # pylint: disable=too-many-locals,too-many-branches,too-many-statements,too-many-nested-blocks
        """Extract agent reasoning steps from workflow checkpoints."""
        if not self.checkpointer or run_id not in self.checkpointer.checkpoints:
            return []

        reasoning_steps = []
        checkpoints = self.checkpointer.checkpoints[run_id]
        step_counter = 1

        # Add initial reasoning
        reasoning_steps.append(
            {
                "step_number": step_counter,
                "step_type": "agent_reasoning",
                "content": "🤖 Agent analyzed request and planned actions",
            }
        )
        step_counter += 1

        for checkpoint in checkpoints:  # pylint: disable=too-many-nested-blocks
            step_name = checkpoint.last_completed_step

            # Try to extract context from checkpoint
            try:
                # Look in the checkpoint's state/context for tool call information
                ctx_store = getattr(checkpoint, "context", None)

                # Debug: Log available context keys for development
                if hasattr(ctx_store, "store") and ctx_store is not None and ctx_store.store:
                    logging.debug("Checkpoint %s context keys: %s", step_name, list(ctx_store.store.keys()))
                if hasattr(ctx_store, "store") and ctx_store is not None and ctx_store.store:
                    # Look for tool calls in the context store
                    for key, value in ctx_store.store.items():
                        if "tool" in key.lower() and hasattr(value, "tool_name"):
                            step = {
                                "step_number": step_counter,
                                "step_type": "tool_call",
                                "content": f"🔧 Tool call: {value.tool_name} with {getattr(value, 'tool_kwargs', {})}",
                            }
                            reasoning_steps.append(step)
                            step_counter += 1

                # Look for tool-related step names and extract detailed info
                if step_name and "call_tool" in step_name:
                    # Try to extract tool call details from context
                    tool_call_info = "⚙️ No tool call requested"
                    if hasattr(ctx_store, "store") and ctx_store is not None and ctx_store.store:
                        for key, value in ctx_store.store.items():
                            if hasattr(value, "tool_name"):
                                tool_name = getattr(value, "tool_name", "unknown")
                                tool_kwargs = getattr(value, "tool_kwargs", {})
                                tool_call_info = f"🔧 Tool call: {tool_name} with {tool_kwargs}"
                                break
                            if "tool_call" in str(key).lower() and hasattr(value, "name"):
                                tool_name = getattr(value, "name", "unknown")
                                tool_input = getattr(value, "tool_input", getattr(value, "input", {}))
                                tool_call_info = f"🔧 Tool call: {tool_name} with {tool_input}"
                                break

                    reasoning_steps.append(
                        {"step_number": step_counter, "step_type": "tool_execution", "content": tool_call_info}
                    )
                    step_counter += 1

                    # Also try to capture tool result if available
                    if hasattr(ctx_store, "store") and ctx_store is not None and ctx_store.store:
                        for key, value in ctx_store.store.items():
                            is_result_key = "result" in str(key).lower() or "output" in str(key).lower()
                            if is_result_key and "tool" in str(key).lower():
                                result_content = str(value)[:150]
                                result_info = (
                                    f"✅ Tool result: {result_content}..."
                                    if len(str(value)) > 150
                                    else f"✅ Tool result: {result_content}"
                                )
                                reasoning_steps.append(
                                    {"step_number": step_counter, "step_type": "tool_result", "content": result_info}
                                )
                                step_counter += 1
                                break
                elif step_name and "run_agent_step" in step_name:
                    reasoning_steps.append(
                        {
                            "step_number": step_counter,
                            "step_type": "agent_thinking",
                            "content": "🧠 Agent processing and deciding on actions",
                        }
                    )
                    step_counter += 1
                elif step_name and "parse_agent_output" in step_name:
                    # Try to extract agent output details from checkpoint events
                    output_info = "📝 Agent parsing output and planning next steps"

                    # Look for actual agent output in checkpoint events
                    checkpoint_attrs = ["output_event", "input_event"]
                    for attr in checkpoint_attrs:
                        if hasattr(checkpoint, attr):
                            value = getattr(checkpoint, attr)
                            if value and hasattr(value, "response"):
                                agent_response = str(getattr(value, "response", ""))
                                if agent_response.strip() and len(agent_response) > 5:
                                    # Truncate long responses for readability
                                    if len(agent_response) > 200:
                                        output_info = f"📝 Agent output: {agent_response[:200]}..."
                                    else:
                                        output_info = f"📝 Agent output: {agent_response}"
                                    break

                    reasoning_steps.append(
                        {"step_number": step_counter, "step_type": "agent_parsing", "content": output_info}
                    )
                    step_counter += 1

            except Exception as e:  # pylint: disable=broad-exception-caught
                # Fallback to basic step information
                logging.debug("Could not extract detailed context from checkpoint: %s", e)
                if step_name not in ["_done", "start"]:  # Skip internal steps
                    reasoning_steps.append(
                        {
                            "step_number": step_counter,
                            "step_type": "workflow_step",
                            "content": f"⚙️ Workflow step: {step_name}",
                        }
                    )
                    step_counter += 1

        # Add final reasoning
        reasoning_steps.append(
            {
                "step_number": step_counter,
                "step_type": "final_reasoning",
                "content": "💭 Agent completed reasoning and generated final response",
            }
        )

        return reasoning_steps

    def _extract_tool_calls_from_reasoning(self, reasoning_steps: List[Dict[str, Any]]) -> List[Any]:
        """Extract tool calls from reasoning steps for deepeval compatibility."""

        tool_calls = []
        for step in reasoning_steps:
            if step.get("step_type") == "tool_call":
                content = step.get("content", "")
                # Parse tool name from content like "🔧 Tool call: create_blueprint with {...}"
                if "Tool call:" in content:
                    parts = content.split("Tool call:", 1)[1].strip()
                    tool_name = parts.split(" with")[0].strip()
                    tool_calls.append(ToolCall(name=tool_name, input_parameters={}))
        return tool_calls

    async def execute_with_reasoning(  # pylint: disable=too-many-locals
        self,
        user_msg: str,
        chat_history: Optional[List[ChatMessage]] = None,
        verbose_logger: Optional[logging.Logger] = None,
        max_iterations: int = 10,
    ) -> Tuple[str, List[Dict[str, Any]], List[Any], List[ChatMessage]]:  # pylint: disable=too-many-locals,too-many-arguments
        """Execute agent with reasoning capture, including partial results on failure."""
        if chat_history is None:
            chat_history = []

        # If verbose_logger provided and we don't have a verbose checkpointer, recreate agent
        if verbose_logger and not isinstance(self.checkpointer, VerboseWorkflowCheckpointer):
            await self._setup_agent(verbose_logger)

        if not self.agent or not self.checkpointer:
            raise ValueError("Agent or checkpointer not initialized")

        # Track run ID for checkpoint extraction on failure
        run_id = None
        partial_reasoning_steps = []
        partial_tool_calls = []

        try:
            if verbose_logger:
                verbose_logger.info("🎬 Starting workflow execution...")
                verbose_logger.info("📝 User message: %s", user_msg)

            # Run agent with checkpointer to capture intermediate steps
            handler = self.checkpointer.run(
                user_msg=user_msg, ctx=self.context, chat_history=chat_history, max_iterations=max_iterations
            )
            run_id = handler.run_id

            if verbose_logger:
                verbose_logger.debug("🏃 Workflow run started with ID: %s", run_id)

            response = await handler

            if verbose_logger:
                verbose_logger.debug("🎉 Workflow completed successfully: %s", run_id)

            # Extract reasoning steps from checkpoints
            reasoning_steps = self._extract_reasoning_from_checkpoints(run_id) if run_id else []

            # Build updated chat history with reasoning steps
            updated_history = chat_history + [ChatMessage(role="user", content=user_msg)]

            # Add reasoning steps to history
            for step in reasoning_steps:
                step_msg = ChatMessage(role="assistant", content=f"[Step {step['step_number']}] {step['content']}")
                updated_history.append(step_msg)

            # Add final response
            updated_history.append(ChatMessage(role="assistant", content=str(response)))

            # Extract tool calls from reasoning steps
            tool_calls = self._extract_tool_calls_from_reasoning(reasoning_steps)

            if verbose_logger:
                verbose_logger.info("🔍 Agent response: %s", response)

            return str(response), reasoning_steps, tool_calls, updated_history

        except Exception as e:  # pylint: disable=broad-exception-caught
            # Extract partial progress even on failure
            self.logger.error("❌ Agent execution failed: %s", e)
            self.logger.info("🔍 Extracting partial progress...")

            if run_id:
                try:
                    partial_reasoning_steps = self._extract_reasoning_from_checkpoints(run_id)
                    partial_tool_calls = self._extract_tool_calls_from_reasoning(partial_reasoning_steps)
                except Exception as extract_error:  # pylint: disable=broad-exception-caught
                    self.logger.warning("⚠️  Could not extract partial steps: %s", extract_error)

            # Pretty print partial progress
            self._pretty_print_partial_progress(
                user_msg, chat_history, partial_reasoning_steps, partial_tool_calls, str(e)
            )

            # Re-raise the original exception
            raise e

    def _pretty_print_partial_progress(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        user_msg: str,
        chat_history: List[ChatMessage],
        reasoning_steps: List[Dict[str, Any]],
        tool_calls: List[Any],
        error_message: str,
    ):
        """Pretty print partial progress when execution fails."""
        self.logger.info("=" * 60)
        self.logger.info("🚫 AGENT EXECUTION FAILURE REPORT")
        self.logger.info("=" * 60)

        self.logger.info("📝 Original Request:")
        self.logger.info("   %s", user_msg)

        self.logger.info("📚 Chat History Length: %d messages", len(chat_history))

        self.logger.info("🧠 Partial Reasoning Steps Captured (%d):", len(reasoning_steps))
        if reasoning_steps:
            for i, step in enumerate(reasoning_steps):
                step_type = step.get("step_type", "unknown")
                content = step.get("content", "No content")
                step_num = step.get("step_number", i + 1)
                self.logger.info("   %2d. [%s] %s", step_num, step_type, content)
        else:
            self.logger.info("   ⚠️  No reasoning steps captured")

        self.logger.info("🔧 Partial Tool Calls Captured (%d):", len(tool_calls))
        if tool_calls:
            for i, tool_call in enumerate(tool_calls):
                if hasattr(tool_call, "name"):
                    self.logger.info("   %d. %s", i + 1, tool_call.name)
                else:
                    self.logger.info("   %d. %s", i + 1, tool_call)
        else:
            self.logger.info("   ⚠️  No tool calls captured")

        self.logger.error("❌ Failure Details:")
        self.logger.error("   Error Message: %s", error_message)

        self.logger.info("💡 Debug Suggestions:")
        if "BadRequestError" in error_message:
            self.logger.info("   - Check tool arguments and parameter validation")
            self.logger.info("   - Verify MCP server is responding correctly")
        elif "WorkflowRuntimeError" in error_message:
            self.logger.info("   - Check max_iterations setting (current: 10)")
            self.logger.info("   - Review agent prompt for infinite loops")
        elif "timeout" in error_message.lower():
            self.logger.info("   - Increase timeout settings")
            self.logger.info("   - Check MCP server responsiveness")
        else:
            self.logger.info("   - Check logs for more detailed error information")
            self.logger.info("   - Verify all dependencies are properly initialized")

        self.logger.info("=" * 60)

    def get_all_checkpoints(self) -> Dict[str, List[Any]]:  # pylint: disable=too-few-public-methods
        """Get all checkpoints across all runs."""
        if not self.checkpointer:
            return {}
        return dict(self.checkpointer.checkpoints)

    def get_checkpoints_for_run(self, run_id: str) -> List[Any]:
        """Get all checkpoints for a specific run ID."""
        if not self.checkpointer or run_id not in self.checkpointer.checkpoints:
            return []
        return self.checkpointer.checkpoints[run_id]


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
