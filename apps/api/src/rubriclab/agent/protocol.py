from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass
class AgentTrace:
    events: list[dict[str, Any]]
    final_output: str
    latency_ms: int
    input_tokens: int
    output_tokens: int


@runtime_checkable
class AgentRunner(Protocol):
    def run(self, input: str, context: str | None = None) -> AgentTrace: ...
