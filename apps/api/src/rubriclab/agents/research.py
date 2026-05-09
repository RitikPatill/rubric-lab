"""
Sample research agent using Anthropic Claude with web_search and calculator tools.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import anthropic

from rubriclab.agents.tools import TOOL_DISPATCH
from rubriclab.runner import TraceEvent, TraceResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool definitions for the Anthropic API
# ---------------------------------------------------------------------------

TOOLS: list[dict[str, Any]] = [
    {
        "name": "web_search",
        "description": "Search the web for current information.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Search query"}},
            "required": ["query"],
        },
    },
    {
        "name": "calculator",
        "description": "Evaluate a mathematical expression.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "A math expression like '1234 * 5678'",
                }
            },
            "required": ["expression"],
        },
    },
]

# ---------------------------------------------------------------------------
# System prompt loading
# ---------------------------------------------------------------------------

_DEFAULT_PROMPT_PATH = Path(__file__).parents[5] / "agents" / "research" / "prompt.md"

_FALLBACK_PROMPT = (
    "You are a research assistant. Use web_search for factual lookups and "
    "calculator for arithmetic. Keep responses concise."
)


def _load_system_prompt(custom: str | None) -> str:
    if custom is not None:
        return custom
    try:
        return _DEFAULT_PROMPT_PATH.read_text(encoding="utf-8").strip()
    except (FileNotFoundError, OSError):
        return _FALLBACK_PROMPT


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# ResearchAgent
# ---------------------------------------------------------------------------


class ResearchAgent:
    def __init__(
        self,
        model: str = "claude-haiku-4-5-20251001",
        api_key: str | None = None,
        system_prompt: str | None = None,
    ) -> None:
        self._client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
        self._model = model
        self._system_prompt = _load_system_prompt(system_prompt)

    def run(self, input: str, context: str | None = None) -> TraceResult:
        t0 = time.monotonic()
        user_text = f"Context:\n{context}\n\n{input}" if context else input
        messages: list[dict] = [{"role": "user", "content": user_text}]
        input_tokens = output_tokens = 0
        events: list[TraceEvent] = []
        final_output = ""

        for _ in range(10):
            resp = self._client.messages.create(
                model=self._model,
                max_tokens=1024,
                system=self._system_prompt,
                tools=TOOLS,
                messages=messages,
            )

            events.append({
                "type": "model_call",
                "timestamp": _now(),
                "content": {
                    "stop_reason": resp.stop_reason,
                    "input_tokens": resp.usage.input_tokens,
                    "output_tokens": resp.usage.output_tokens,
                },
            })
            input_tokens += resp.usage.input_tokens
            output_tokens += resp.usage.output_tokens

            if resp.stop_reason == "tool_use":
                tool_use_blocks = [b for b in resp.content if b.type == "tool_use"]
                results: list[str] = []

                for block in tool_use_blocks:
                    events.append({
                        "type": "tool_call",
                        "timestamp": _now(),
                        "content": {
                            "tool_name": block.name,
                            "tool_input": block.input,
                            "tool_use_id": block.id,
                        },
                    })
                    result_str = self._execute_tool(block.name, block.input)
                    results.append(result_str)
                    events.append({
                        "type": "tool_result",
                        "timestamp": _now(),
                        "content": {
                            "tool_use_id": block.id,
                            "result": result_str,
                        },
                    })

                # Anthropic multi-turn format: pass raw content blocks, SDK serialises them
                messages.append({"role": "assistant", "content": resp.content})
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result_str,
                        }
                        for block, result_str in zip(tool_use_blocks, results)
                    ],
                })
            else:
                # end_turn or other stop reason
                for block in resp.content:
                    if block.type == "text":
                        final_output = block.text
                        break
                events.append({
                    "type": "final_output",
                    "timestamp": _now(),
                    "content": {"text": final_output},
                })
                break
        else:
            logger.warning("ResearchAgent hit max iterations (10); trace may be incomplete")
            final_output = "[max iterations reached]"
            events.append({
                "type": "final_output",
                "timestamp": _now(),
                "content": {"text": final_output},
            })

        latency_ms = int((time.monotonic() - t0) * 1000)
        return TraceResult(
            events=events,
            final_output=final_output,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    def _execute_tool(self, name: str, tool_input: dict) -> str:
        fn = TOOL_DISPATCH.get(name)
        if fn is None:
            return f"[error] Unknown tool: {name}"
        try:
            return fn(tool_input)
        except Exception as exc:
            return f"[error] {exc}"
