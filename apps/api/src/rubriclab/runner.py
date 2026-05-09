"""
Shared types for the RubricLab agent runner protocol.
Defines trace types, the AgentRunner protocol, and run_case persistence helper.
No Anthropic calls.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, TypedDict, runtime_checkable

from sqlmodel import Session

from .models import Case, CaseResult, Trace
from .repository import create_case_result, create_rubric_score, create_trace

if TYPE_CHECKING:
    from .judge import JudgeEngine

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


# Backward-compatible aliases
RunResult = TraceResult


@runtime_checkable
class AgentRunner(Protocol):
    """Structural protocol — any class with a matching run() satisfies it."""

    def run(self, input: str, context: str | None = None) -> TraceResult: ...


def run_case(
    session: Session,
    run_id: str,
    case: Case,
    runner: AgentRunner,
    judge: JudgeEngine | None = None,
) -> tuple[CaseResult, Trace]:
    """Execute one test case and persist CaseResult + Trace.
    If a JudgeEngine is provided and the case has rubric dimensions,
    scores are computed and persisted as RubricScore rows.
    """
    result = runner.run(case.input, case.context)

    case_result = create_case_result(session, run_id, case.id, passed=False)
    trace = create_trace(
        session,
        case_result.id,
        result.events,
        latency_ms=result.latency_ms,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
    )

    if judge is not None and case.rubric:
        judge_result = judge.score(result, case.rubric, case.expected_behavior, case.input)
        for ds in judge_result.dimension_scores:
            create_rubric_score(
                session, case_result.id, ds.dimension_id, ds.score, ds.justification,
                dimension_name=ds.dimension_name,
            )
        case_result.passed = judge_result.passed
        session.add(case_result)
        session.commit()
        session.refresh(case_result)

    return case_result, trace
