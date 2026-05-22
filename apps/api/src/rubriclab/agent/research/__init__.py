import logging
import time
from datetime import datetime, timezone
from typing import Any

import anthropic

from rubriclab.agent.protocol import AgentTrace
from rubriclab.agent.research.tools import TOOLS, calculator, web_search

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat() + "Z"


class ResearchAgent:
    MODEL = "claude-haiku-4-5-20251001"
    MAX_ITERATIONS = 10

    def __init__(self, client: anthropic.Anthropic | None = None) -> None:
        self._client = client or anthropic.Anthropic()

    def _dispatch_tool(self, name: str, input: dict[str, Any]) -> str:
        if name == "web_search":
            return web_search(input.get("query", ""))
        if name == "calculator":
            return calculator(input.get("expression", ""))
        raise ValueError(f"Unknown tool: {name}")

    def run(self, input: str, context: str | None = None) -> AgentTrace:
        start = time.monotonic()
        events: list[dict[str, Any]] = []
        total_input_tokens = 0
        total_output_tokens = 0

        messages: list[dict[str, Any]] = [{"role": "user", "content": input}]
        final_output = ""

        for _ in range(self.MAX_ITERATIONS):
            kwargs: dict[str, Any] = {
                "model": self.MODEL,
                "max_tokens": 1024,
                "tools": TOOLS,
                "messages": messages,
            }
            if context:
                kwargs["system"] = context

            response = self._client.messages.create(**kwargs)
            total_input_tokens += response.usage.input_tokens
            total_output_tokens += response.usage.output_tokens

            # Emit message event for any text blocks in this response
            text_parts = [b.text for b in response.content if b.type == "text"]
            if text_parts:
                events.append({
                    "type": "message",
                    "timestamp": _now(),
                    "content": {"role": "assistant", "text": " ".join(text_parts)},
                })

            if response.stop_reason != "tool_use":
                final_output = " ".join(text_parts)
                break

            # Process tool_use blocks
            tool_results_content: list[dict[str, Any]] = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                events.append({
                    "type": "tool_call",
                    "timestamp": _now(),
                    "content": {"tool": block.name, "tool_use_id": block.id, "input": block.input},
                })
                result = self._dispatch_tool(block.name, block.input)
                events.append({
                    "type": "tool_result",
                    "timestamp": _now(),
                    "content": {"tool": block.name, "tool_use_id": block.id, "result": result},
                })
                tool_results_content.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results_content})
        else:
            logger.warning(
                "ResearchAgent hit MAX_ITERATIONS (%d), returning partial trace",
                self.MAX_ITERATIONS,
            )

        end = time.monotonic()
        return AgentTrace(
            events=events,
            final_output=final_output,
            latency_ms=int((end - start) * 1000),
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
        )
