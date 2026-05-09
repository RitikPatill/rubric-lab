import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import anthropic

from rubriclab.runner import RunResult

# ---------------------------------------------------------------------------
# Tool definitions for the Anthropic API
# ---------------------------------------------------------------------------

TOOLS: list[dict[str, Any]] = [
    {
        "name": "web_search",
        "description": "Search the web for factual information. Returns a short text snippet.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Search query"}},
            "required": ["query"],
        },
    },
    {
        "name": "calculator",
        "description": "Evaluate an arithmetic expression. Input must be a valid Python numeric expression.",
        "input_schema": {
            "type": "object",
            "properties": {"expression": {"type": "string", "description": "e.g. '1234 * 5678'"}},
            "required": ["expression"],
        },
    },
]

# ---------------------------------------------------------------------------
# Stub tool implementations
# ---------------------------------------------------------------------------


def _web_search(query: str) -> str:
    q = query.lower()
    if "tokyo" in q and "population" in q:
        return "Tokyo's population is approximately 37.4 million (2023 estimate)."
    if "boiling" in q and "water" in q:
        return "Water boils at 100 degrees Celsius (212 degrees Fahrenheit) at sea level."
    if "capital" in q and "france" in q:
        return "The capital of France is Paris."
    if "telephone" in q:
        return "The telephone was invented by Alexander Graham Bell in 1876."
    return f"No specific results found for: {query}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DEFAULT_SYSTEM_PROMPT = (
    "You are a research assistant. Use web_search for factual lookups and "
    "calculator for arithmetic. Keep responses concise."
)


def _find_system_prompt() -> str:
    """Walk up from __file__ looking for agents/research/prompt.md."""
    # Try RUBRICLAB_ROOT env var first
    root_env = os.environ.get("RUBRICLAB_ROOT")
    if root_env:
        candidate = Path(root_env) / "agents" / "research" / "prompt.md"
        if candidate.exists():
            return candidate.read_text(encoding="utf-8").strip()

    # Walk up from this file until we find agents/research/prompt.md
    current = Path(__file__).resolve()
    for _ in range(7):
        current = current.parent
        candidate = current / "agents" / "research" / "prompt.md"
        if candidate.exists():
            return candidate.read_text(encoding="utf-8").strip()

    return _DEFAULT_SYSTEM_PROMPT


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


# ---------------------------------------------------------------------------
# ResearchAgent
# ---------------------------------------------------------------------------


class ResearchAgent:
    def __init__(
        self,
        *,
        client: anthropic.Anthropic | None = None,
        model: str = "claude-haiku-4-5-20251001",
        system_prompt: str | None = None,
        max_tokens: int = 1024,
    ) -> None:
        self._client = client or anthropic.Anthropic()
        self._model = model
        self._system_prompt = system_prompt if system_prompt is not None else _find_system_prompt()
        self._max_tokens = max_tokens

    def _calculator(self, expression: str) -> str:
        try:
            result = eval(expression, {"__builtins__": None}, {})  # noqa: S307
            return str(result)
        except Exception as exc:
            return f"Error evaluating expression: {exc}"

    def run(self, input: str, context: str | None = None) -> RunResult:
        user_content = input if context is None else f"{context}\n\n{input}"
        messages: list[dict] = [{"role": "user", "content": user_content}]

        start = time.monotonic()
        total_input_tokens = 0
        total_output_tokens = 0
        events: list[dict] = []
        final_output = ""

        for _ in range(10):
            response = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=self._system_prompt,
                tools=TOOLS,
                messages=messages,
            )

            total_input_tokens += response.usage.input_tokens
            total_output_tokens += response.usage.output_tokens

            # Append assistant turn before processing blocks
            messages.append({"role": "assistant", "content": response.content})

            tool_use_blocks: list[tuple[Any, str]] = []
            for block in response.content:
                if block.type == "text":
                    events.append(
                        {
                            "type": "message",
                            "timestamp": _now(),
                            "content": {"role": "assistant", "text": block.text},
                        }
                    )
                    final_output = block.text
                elif block.type == "tool_use":
                    events.append(
                        {
                            "type": "tool_call",
                            "timestamp": _now(),
                            "content": {
                                "tool": block.name,
                                "input": block.input,
                                "tool_use_id": block.id,
                            },
                        }
                    )
                    if block.name == "web_search":
                        tool_output = _web_search(block.input.get("query", ""))
                    elif block.name == "calculator":
                        tool_output = self._calculator(block.input.get("expression", ""))
                    else:
                        tool_output = f"Unknown tool: {block.name}"

                    events.append(
                        {
                            "type": "tool_result",
                            "timestamp": _now(),
                            "content": {"tool_use_id": block.id, "output": tool_output},
                        }
                    )
                    tool_use_blocks.append((block, tool_output))

            if response.stop_reason == "end_turn" or not tool_use_blocks:
                break

            # Build tool result message and continue
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {"type": "tool_result", "tool_use_id": blk.id, "content": out}
                        for blk, out in tool_use_blocks
                    ],
                }
            )
        else:
            print("WARNING: agent loop hit max iterations (10)", file=sys.stderr)

        return RunResult(
            events=events,
            final_output=final_output,
            latency_ms=int((time.monotonic() - start) * 1000),
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
        )
