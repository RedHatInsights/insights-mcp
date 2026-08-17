"""Probe OpenAI-compatible chat/completions tool calling for LLM matrix configs.

Use this to see whether a gateway returns structured ``tool_calls`` (what LlamaIndex
``FunctionAgent`` needs) or only prose/code fences in ``content``.

Run all configs from ``test_config.json``:

    uv run python tests/llm_tool_call_probe.py

Run one config by name (substring match, case-insensitive):

    uv run python tests/llm_tool_call_probe.py --name mistral

Pytest (included in ``make test`` when ``test_config.json`` has valid LLM entries):

    uv run pytest tests/llm_tool_call_probe.py -v
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import pytest
import requests
from mcp_llm_eval.utils import load_llm_configurations, should_skip_llm_matrix_tests

PROBE_TOOL_NAME = "image-builder__get_blueprints"
PROBE_USER_MESSAGE = "List my latest 2 blueprints"

_PROBE_TOOL_SCHEMA: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": PROBE_TOOL_NAME,
        "description": (
            "Show user's image blueprints (saved image templates/configurations). "
            "CALL IMMEDIATELY when the user asks to list blueprints."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of blueprints to return.",
                },
                "offset": {
                    "type": "integer",
                    "description": "Number of blueprints to skip when paging.",
                },
                "search_string": {
                    "type": "string",
                    "description": "Optional name substring filter.",
                },
            },
        },
    },
}

llm_configurations, _ = load_llm_configurations()


def _chat_completions_url(model_api: str) -> str:
    base = model_api.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return f"{base}/chat/completions"


def _build_payload(model_id: str, force_tool: bool) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model_id,
        "messages": [{"role": "user", "content": PROBE_USER_MESSAGE}],
        "tools": [_PROBE_TOOL_SCHEMA],
        "temperature": 0.1,
    }
    if force_tool:
        payload["tool_choice"] = {
            "type": "function",
            "function": {"name": PROBE_TOOL_NAME},
        }
    return payload


def probe_tool_calling(
    llm_config: dict[str, str],
    *,
    force_tool: bool = False,
    timeout: float = 120,
) -> dict[str, Any]:
    """POST one chat/completions request and summarize tool-call vs content response."""
    model_api = llm_config["MODEL_API"]
    model_id = llm_config["MODEL_ID"]
    url = _chat_completions_url(model_api)
    headers = {
        "Authorization": f"Bearer {llm_config['USER_KEY']}",
        "Content-Type": "application/json",
    }
    payload = _build_payload(model_id, force_tool)

    result: dict[str, Any] = {
        "name": llm_config.get("name", model_id),
        "model_id": model_id,
        "url": url,
        "force_tool": force_tool,
        "http_status": None,
        "error": None,
        "tool_calls": [],
        "content_preview": "",
        "has_tool_calls": False,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        result["http_status"] = response.status_code
        if response.status_code != 200:
            result["error"] = response.text[:2000]
            return result

        body = response.json()
        choices = body.get("choices") or []
        if not choices:
            result["error"] = f"no choices in response: {json.dumps(body)[:500]}"
            return result

        message = choices[0].get("message") or {}
        tool_calls = message.get("tool_calls") or []
        content = message.get("content") or ""
        if isinstance(content, list):
            content = json.dumps(content)

        result["tool_calls"] = tool_calls
        result["has_tool_calls"] = bool(tool_calls)
        result["content_preview"] = str(content)[:500]
    except requests.RequestException as exc:
        result["error"] = str(exc)

    return result


def _print_probe_report(probe: dict[str, Any]) -> None:
    label = "forced tool_choice" if probe["force_tool"] else "default tool_choice"
    print(f"\n=== {probe['name']} ({probe['model_id']}) [{label}] ===")
    print(f"POST {probe['url']}")
    if probe["error"]:
        print(f"ERROR: {probe['error']}")
        return
    print(f"HTTP {probe['http_status']}")
    print(f"has_tool_calls: {probe['has_tool_calls']}")
    if probe["tool_calls"]:
        print(f"tool_calls: {json.dumps(probe['tool_calls'], indent=2)}")
    if probe["content_preview"]:
        print(f"content (first 500 chars): {probe['content_preview']!r}")


def _select_configs(name_filter: str | None) -> list[dict[str, str]]:
    if not llm_configurations:
        return []

    typed_configs = [
        {
            "name": str(config["name"]),
            "MODEL_API": str(config["MODEL_API"]),
            "MODEL_ID": str(config["MODEL_ID"]),
            "USER_KEY": str(config["USER_KEY"]),
        }
        for config in llm_configurations
    ]

    if not name_filter:
        return typed_configs

    needle = name_filter.lower()
    matched = [config for config in typed_configs if needle in config["name"].lower()]
    if not matched:
        available = ", ".join(config["name"] for config in typed_configs)
        raise SystemExit(f"No config matched --name {name_filter!r}. Available: {available}")
    return matched


def run_probes(name_filter: str | None = None, *, force_tool: bool = False) -> list[dict[str, Any]]:
    """Run probe(s) and print reports; return raw results."""
    configs = _select_configs(name_filter)
    if not configs:
        raise SystemExit("No LLM configurations found (missing or empty test_config.json).")

    results: list[dict[str, Any]] = []
    for config in configs:
        probe = probe_tool_calling(config, force_tool=force_tool)
        results.append(probe)
        _print_probe_report(probe)
    return results


def _probe_passed(probe: dict[str, Any]) -> bool:
    return probe.get("http_status") == 200 and probe.get("has_tool_calls") is True


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Probe OpenAI-compatible tool calling for test_config LLMs.",
    )
    parser.add_argument(
        "--name",
        help="Run only configs whose name contains this substring (case-insensitive).",
    )
    parser.add_argument(
        "--force-tool",
        action="store_true",
        help="Also send tool_choice forcing image-builder__get_blueprints.",
    )
    parser.add_argument(
        "--compare-force",
        action="store_true",
        help="Run default request, then the same config with --force-tool.",
    )
    args = parser.parse_args(argv)

    results = run_probes(args.name, force_tool=False)
    if args.compare_force or args.force_tool:
        results.extend(run_probes(args.name, force_tool=True))

    if not results:
        return 1

    failures = [probe for probe in results if not _probe_passed(probe)]
    if failures:
        print(f"\n{len(failures)} probe(s) did not return tool_calls.")
        return 1
    print("\nAll probes returned tool_calls.")
    return 0


@pytest.mark.skipif(should_skip_llm_matrix_tests(), reason="No valid LLM configurations found")
@pytest.mark.llm
class TestLLMToolCallProbe:
    """Live probe: OpenAI-compatible gateways must return tool_calls for the paging prompt."""

    @pytest.mark.parametrize(
        "llm_config",
        llm_configurations,
        ids=[str(config["name"]) for config in llm_configurations],
    )
    def test_chat_completions_returns_tool_calls(self, llm_config: dict[str, str | None]) -> None:
        typed_config = {
            "name": str(llm_config["name"]),
            "MODEL_API": str(llm_config["MODEL_API"]),
            "MODEL_ID": str(llm_config["MODEL_ID"]),
            "USER_KEY": str(llm_config["USER_KEY"]),
        }
        probe = probe_tool_calling(typed_config)
        assert probe["http_status"] == 200, probe.get("error") or probe
        assert probe["has_tool_calls"], (
            f"expected tool_calls for {typed_config['name']}; got content only: {probe['content_preview']!r}"
        )


if __name__ == "__main__":
    sys.exit(main())
