"""
Shared types for the RubricLab agent runner protocol.
Pure data-shape definitions — no I/O, no Anthropic calls.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol, TypedDict, runtime_checkable

logger = logging.getLogger(__name__)


class TraceEvent(TypedDict):
    """One event in an agent execution trace."""

    type: str       # "model_call" | "tool_call" | "tool_result" | "final_output"
    timestamp: str  # UTC ISO-8601
    content: dict   # type-specific payload


@dataclass
class TraceResult:
    """Value object returned by every AgentRunner.run() call."""

    events: list[TraceEvent]
    final_output: str
    latency_ms: int
    input_tokens: int
    output_tokens: int


@runtime_checkable
class AgentRunner(Protocol):
    """Structural protocol — any class with a matching run() satisfies it."""

    def run(self, input: str, context: str | None = None) -> TraceResult: ...
