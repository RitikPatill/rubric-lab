import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import anthropic

from rubriclab.agent import AgentTrace
from rubriclab.agents.tools import TOOL_DISPATCH

# ---------------------------------------------------------------------------
# Tool definitions for the Anthropic messages API
# ---------------------------------------------------------------------------

TOOL_DEFS: list[dict[str, Any]] = [
    {
        "name": "web_search",
        "description": "Search the web for current information about any topic.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "calculator",
        "description": "Evaluate a mathematical expression and return the result.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "A math expression like '6 * 7' or '1,234 × 5,678'",
                },
            },
            "required": ["expression"],
        },
    },
]

# ---------------------------------------------------------------------------
# System prompt loading
# ---------------------------------------------------------------------------

_DEFAULT_PROMPT = (
    "You are a research assistant. Use web_search for factual lookups and "
    "calculator for arithmetic. Keep responses concise."
)


def _load_system_prompt(prompt_path: str | None) -> str:
    try:
        if prompt_path:
            return Path(prompt_path).read_text(encoding="utf-8").strip()
        repo_root = Path(__file__).parents[5]
        return (repo_root / "agents" / "research" / "prompt.md").read_text(encoding="utf-8").strip()
    except (FileNotFoundError, OSError, IndexError):
        return _DEFAULT_PROMPT


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# ResearchAgent
# ---------------------------------------------------------------------------

_MAX_ITERATIONS = 10


class ResearchAgent:
    def __init__(
        self,
        model: str = os.getenv("RESEARCH_AGENT_MODEL", "claude-haiku-4-5-20251001"),
        prompt_path: str | None = None,
    ) -> None:
        self.client = anthropic.Anthropic()
        self.model = model
        self._system = _load_system_prompt(prompt_path)

    def run(self, input: str, context: str | None = None) -> AgentTrace:
        start = time.perf_counter()
        events: list[dict] = []
        total_input_tokens = 0
        total_output_tokens = 0
        final_output = ""

        full_input = input if context is None else f"{context}\n\n{input}"
        messages: list[dict] = [{"role": "user", "content": full_input}]

        for _ in range(_MAX_ITERATIONS):
            call_start = time.perf_counter()
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=self._system,
                tools=TOOL_DEFS,
                messages=messages,
            )
            call_latency_ms = int((time.perf_counter() - call_start) * 1000)

            total_input_tokens += response.usage.input_tokens
            total_output_tokens += response.usage.output_tokens

            events.append({
                "type": "model_call",
                "timestamp": _now(),
                "model": self.model,
                "latency_ms": call_latency_ms,
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            })

            if response.stop_reason == "end_turn":
                for block in response.content:
                    if block.type == "text":
                        final_output = block.text
                        break
                events.append({
                    "type": "final_output",
                    "timestamp": _now(),
                    "content": final_output,
                })
                break

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue

                    events.append({
                        "type": "tool_call",
                        "timestamp": _now(),
                        "tool_use_id": block.id,
                        "tool_name": block.name,
                        "input": block.input,
                    })

                    dispatch = TOOL_DISPATCH.get(block.name)
                    if dispatch:
                        try:
                            result = dispatch(block.input)
                        except ValueError as exc:
                            result = f"Error: {exc}"
                    else:
                        result = f"Unknown tool: {block.name}"

                    events.append({
                        "type": "tool_result",
                        "timestamp": _now(),
                        "tool_use_id": block.id,
                        "tool_name": block.name,
                        "output": result,
                    })
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})
        else:
            raise RuntimeError(f"Agent exceeded maximum iterations ({_MAX_ITERATIONS})")

        latency_ms = int((time.perf_counter() - start) * 1000)
        return AgentTrace(
            events=events,
            final_output=final_output,
            latency_ms=latency_ms,
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
        )
