"""Utility functions for testing."""

import os
import json
import logging
import socket
import time
import asyncio
import multiprocessing
from typing import Dict, List, Any, Tuple, Optional

import requests
from llama_index.core.llms import ChatMessage
from pydantic import BaseModel
from deepeval.models.base_model import DeepEvalBaseLLM


# Constants
DEFAULT_JSON_HEADERS = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}


def should_skip_llm_tests() -> bool:
    """Check if LLM integration tests should be skipped."""
    required_vars = ["MODEL_API", "MODEL_ID", "USER_KEY"]
    return not all(os.getenv(var) for var in required_vars)


def load_llm_configurations() -> Tuple[List[Dict[str, Optional[str]]], Optional[Dict[str, str]]]:
    """Load LLM configurations from test_config.json file."""
    config_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "test_config.json")

    if not os.path.exists(config_file):
        # Fallback to environment variables for backward compatibility
        if not should_skip_llm_tests():
            return [
                {
                    "name": "Default Model",
                    "MODEL_API": os.getenv("MODEL_API"),
                    "MODEL_ID": os.getenv("MODEL_ID"),
                    "USER_KEY": os.getenv("USER_KEY"),
                }
            ], None
        return [], None

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        configurations = []
        for llm_config in config.get("llm_configurations", []):
            # Substitute environment variables in configuration
            resolved_config: Dict[str, Optional[str]] = {}
            for key, value in llm_config.items():
                if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                    env_var = value[2:-1]  # Remove ${ and }
                    resolved_value = os.getenv(env_var)
                    if resolved_value:
                        resolved_config[key] = resolved_value
                    else:
                        # Skip this configuration if required env var is missing
                        break
                else:
                    resolved_config[key] = value

            # Only add configuration if all required variables are present
            if all(key in resolved_config and resolved_config[key] for key in ["MODEL_API", "MODEL_ID", "USER_KEY"]):
                configurations.append(resolved_config)
        guardian_llm: Optional[Dict[str, str]] = config.get("guardian_llm")
        return configurations, guardian_llm

    except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
        logging.warning("Error loading test_config.json: %s. Falling back to environment variables.", e)
        # Fallback to environment variables
        if not should_skip_llm_tests():
            return [
                {
                    "name": "Default Model",
                    "MODEL_API": os.getenv("MODEL_API"),
                    "MODEL_ID": os.getenv("MODEL_ID"),
                    "USER_KEY": os.getenv("USER_KEY"),
                }
            ], None
        return [], None


def should_skip_llm_matrix_tests() -> bool:
    """Check if LLM matrix tests should be skipped."""
    configurations, _ = load_llm_configurations()
    return len(configurations) == 0


def cleanup_server_process(server_process: multiprocessing.Process) -> None:
    """Helper function to properly cleanup a server process."""
    if server_process.is_alive():
        server_process.terminate()
        server_process.join(timeout=5)
        if server_process.is_alive():
            server_process.kill()


class ServerStartupError(Exception):
    """Exception raised when MCP server fails to start."""


class ServerConnectionError(Exception):
    """Exception raised when unable to connect to MCP server."""


class MCPError(Exception):
    """Exception raised for MCP-related errors."""


def get_free_port() -> int:
    """Find a free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


def start_mcp_server_process():
    """Start MCP server in a separate process - shared utility function."""
    port = get_free_port()
    server_url = f"http://127.0.0.1:{port}/mcp/"

    # Use multiprocessing instead of threading to avoid asyncio conflicts
    server_queue = multiprocessing.Queue()

    def server_process():
        """Start the MCP server in a separate process."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Import here to avoid module-level asyncio conflicts
            # pylint: disable=import-outside-toplevel
            from image_builder_mcp.server import ImageBuilderMCP

            # Get credentials from environment (may be None for testing)
            client_id = os.getenv("INSIGHTS_CLIENT_ID")
            client_secret = os.getenv("INSIGHTS_CLIENT_SECRET")

            mcp_server = ImageBuilderMCP()
            mcp_server.init_insights_client(
                client_id=client_id,
                client_secret=client_secret,
                oauth_enabled=False,
                mcp_transport="http",
            )
            mcp_server.register_tools()

            # Signal that server is starting
            server_queue.put("starting")

            # Start server with HTTP transport on dynamic port
            mcp_server.run(transport="http", host="127.0.0.1", port=port)

        except Exception as e:  # pylint: disable=broad-exception-caught
            server_queue.put(f"error: {e}")

    # Start server process
    server_process = multiprocessing.Process(target=server_process, daemon=True)
    server_process.start()

    try:
        # Wait for server to start
        start_signal = server_queue.get(timeout=10)
        if start_signal.startswith("error:"):
            raise ServerStartupError(f"Server failed to start: {start_signal}")

        # Additional wait for server to be fully ready
        time.sleep(3)

        # Test server connectivity with retry logic
        max_retries = 5
        for attempt in range(max_retries):
            try:
                test_request = create_mcp_init_request()
                response = requests.post(server_url, json=test_request, headers=DEFAULT_JSON_HEADERS, timeout=10)

                if response.status_code == 200:
                    break

                if attempt == max_retries - 1:
                    raise ServerConnectionError(
                        (
                            f"Server not responding properly after {max_retries} "
                            f"attempts: {response.status_code} - {response.text}"
                        )
                    )

                time.sleep(2)  # Wait before retry

            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    raise ServerConnectionError(f"Failed to connect to server after {max_retries} attempts: {e}") from e
                time.sleep(2)  # Wait before retry

        return server_url, server_process

    except Exception as e:  # pylint: disable=broad-exception-caught
        cleanup_server_process(server_process)
        raise e


def parse_mcp_response(response_text: str) -> Dict[str, Any]:
    """Parse MCP response which could be JSON or SSE format."""
    try:
        return json.loads(response_text)
    except json.JSONDecodeError as exc:
        # Try parsing as SSE format
        for line in response_text.split("\n"):
            if line.startswith("data: "):
                data_part = line[6:]  # Remove 'data: ' prefix
                try:
                    return json.loads(data_part)
                except json.JSONDecodeError:
                    continue
        raise ValueError(f"No valid JSON found in response: {response_text}") from exc


def make_llm_api_request(api_url: str, api_key: str, payload: Dict[str, Any]) -> str:
    """Make HTTP request to LLM API and return response content."""
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

    try:
        response = requests.post(f"{api_url}/chat/completions", json=payload, headers=headers, timeout=60)
        response.raise_for_status()

        result = response.json()
        return result["choices"][0]["message"]["content"]

    except requests.exceptions.RequestException as e:
        raise MCPError(f"LLM query failed: {e}") from e
    except (KeyError, IndexError) as e:
        raise MCPError(f"Unexpected LLM response format: {e}") from e


def call_llm_api(
    api_url: str, model_id: str, api_key: str, messages: List[Dict[str, str]], temperature: float = 0.1
) -> str:
    """Call LLM API with messages and return response content."""
    payload = {
        "model": model_id,
        "messages": messages,
        "temperature": temperature,
    }

    return make_llm_api_request(api_url, api_key, payload)


def create_mcp_init_request() -> dict:
    """Create standard MCP initialization request."""
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"},
        },
    }


def pretty_print_chat_history(
    conversation_history: List[ChatMessage], llm_name: str, verbose_logger: logging.Logger
) -> None:
    """Pretty print chat history for debugging."""
    verbose_logger.info("Full conversation history:")

    if len(conversation_history) == 0:
        verbose_logger.info("No conversation history")
        return

    for i, turn in enumerate(conversation_history):
        if turn.role == "user":
            verbose_logger.info(f"{llm_name} turn {i + 1}: 👤 User: {turn.content}")
        elif turn.role == "assistant":
            verbose_logger.info(f"{llm_name} turn {i + 1}: 🤖 Assistant: {turn.content}")
        elif turn.role == "tool":
            verbose_logger.info(f"{llm_name} turn {i + 1}: 🔧 Tool: {turn.content}")
        else:
            verbose_logger.info(f"{llm_name} turn {i + 1}: ? {turn.role}: {turn.content}")


class CustomVLLMModel(DeepEvalBaseLLM):
    """Custom LLM model for deepeval that uses vLLM with OpenAI-compatible API.

    Current implementation of deepeval does not support vLLM Server with api_key yet.
    And the OpenAI class does not support custom models.
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        model_id: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: float = 0,
        **kwargs,
    ):
        if not api_url:
            raise ValueError("api_url must be provided for CustomVLLMModel")
        if not model_id:
            raise ValueError("model_id must be provided for CustomVLLMModel")

        self.api_url = api_url
        self.model_id = model_id or "default"
        self.api_key = api_key or ""

        if temperature < 0:
            raise ValueError("Temperature must be >= 0.")
        self.temperature = temperature
        super().__init__(self.model_id)

    # pylint: disable=arguments-differ
    def generate(  # type: ignore[override]
        self, prompt: str, schema: Optional[BaseModel] = None
    ) -> Any:
        # For simple cases without schema, use shared function
        if not schema:
            messages = [{"role": "user", "content": prompt}]
            return call_llm_api(self.api_url, self.model_id, self.api_key, messages, self.temperature)

        # For schema validation, use shared HTTP request function
        payload = {
            "model": self.model_id,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
        }

        content = make_llm_api_request(self.api_url, self.api_key, payload)

        if schema:
            try:
                # remove markdown code block markers
                content = content.replace("```json", "").replace("```", "")
                return schema.model_validate_json(content)
                # print(f"Model {self.model_id} replied for {payload}\ņwith {ret}")
            except Exception as e:  # pylint: disable=broad-exception-caught
                error_message = (
                    f"The LLM {self.model_id} was expected to return a valid JSON object "
                    f"compatible with the schema {schema}. but it returned {content}."
                    f"Error: {e}"
                )
                raise ValueError(error_message) from e

        return content

    # pylint: disable=arguments-differ
    async def a_generate(  # type: ignore[override]
        self, prompt: str, schema: Optional[BaseModel] = None
    ) -> str:
        # For simplicity, reuse sync version
        return self.generate(prompt, schema)

    def load_model(self):
        # For API-based models, we don't need to load anything
        return None

    def get_model_name(self):
        return f"{self.model_id} (vLLM)"
