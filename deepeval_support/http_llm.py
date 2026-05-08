"""OpenAI-compatible chat-completions helpers for Deepeval custom models."""

from typing import Any, Dict, List

import requests

from deepeval_support.errors import MCPError


def make_llm_api_request(api_url: str, api_key: str, payload: Dict[str, Any]) -> str:
    """Make HTTP request to LLM API and return response message content."""
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

    try:
        response = requests.post(f"{api_url}/chat/completions", json=payload, headers=headers, timeout=60)
        response.raise_for_status()

        result = response.json()
        return result["choices"][0]["message"]["content"]

    except requests.exceptions.RequestException as exc:
        raise MCPError(f"LLM query failed: {exc}") from exc
    except (KeyError, IndexError) as exc:
        raise MCPError(f"Unexpected LLM response format: {exc}") from exc


def call_llm_api(
    api_url: str, model_id: str, api_key: str, messages: List[Dict[str, str]], temperature: float = 0.1
) -> str:
    """Call LLM chat-completions API and return assistant message content."""
    payload = {
        "model": model_id,
        "messages": messages,
        "temperature": temperature,
    }

    return make_llm_api_request(api_url, api_key, payload)


__all__ = ["call_llm_api", "make_llm_api_request"]
