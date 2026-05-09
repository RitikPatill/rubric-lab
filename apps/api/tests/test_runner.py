"""M3 tests: tool helpers, AgentRunner protocol, and run_case() persistence."""
import pytest

from rubriclab.agents.research import calculate, web_search
from rubriclab.runner import AgentResult, AgentRunner, run_case
from rubriclab.repository import get_trace
from rubriclab.seed import seed_demo_suite


# ---------------------------------------------------------------------------
# StubRunner — no API calls required
# ---------------------------------------------------------------------------


class StubRunner:
    def run(self, input: str, context: str | None = None) -> AgentResult:
        return AgentResult(
            output="42",
            events=[{"type": "final_output", "timestamp": "2024-01-01T00:00:00", "content": "42"}],
            latency_ms=100,
            input_tokens=10,
            output_tokens=5,
        )


# ---------------------------------------------------------------------------
# calculate() unit tests
# ---------------------------------------------------------------------------


def test_calculate_multiplication():
    assert calculate("1234 * 5678") == 7006652


def test_calculate_division():
    assert abs(calculate("150 / 2.5") - 60.0) < 1e-9


def test_calculate_addition():
    assert calculate("1 + 2") == 3


def test_calculate_rejects_function_calls():
    with pytest.raises(ValueError):
        calculate("__import__('os')")


# ---------------------------------------------------------------------------
# web_search() unit tests
# ---------------------------------------------------------------------------


def test_web_search_returns_string():
    result = web_search("anything")
    assert isinstance(result, str) and len(result) > 0


def test_web_search_tokyo():
    result = web_search("population of tokyo")
    assert "million" in result or "37" in result


def test_web_search_boiling():
    result = web_search("boiling point of water")
    assert "100" in result


def test_web_search_unknown_returns_fallback():
    result = web_search("xyzzy gobbledygook unknown query abc123")
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# AgentRunner protocol check
# ---------------------------------------------------------------------------


def test_agent_runner_protocol():
    stub = StubRunner()
    assert isinstance(stub, AgentRunner)


# ---------------------------------------------------------------------------
# run_case() persistence tests
# ---------------------------------------------------------------------------


def test_run_case_creates_case_result(session):
    suite = seed_demo_suite(session)
    from rubriclab.repository import list_cases, create_run

    cases = list_cases(session, suite.id)
    run = create_run(session, suite.id)

    case_result = run_case(session, StubRunner(), run.id, cases[0])

    assert case_result is not None
    assert case_result.passed is False


def test_run_case_creates_trace(session):
    suite = seed_demo_suite(session)
    from rubriclab.repository import list_cases, create_run

    cases = list_cases(session, suite.id)
    run = create_run(session, suite.id)

    case_result = run_case(session, StubRunner(), run.id, cases[0])
    trace = get_trace(session, case_result.id)

    assert trace is not None
    assert trace.latency_ms == 100
    assert len(trace.events) == 1


def test_run_case_preserves_tokens(session):
    suite = seed_demo_suite(session)
    from rubriclab.repository import list_cases, create_run

    cases = list_cases(session, suite.id)
    run = create_run(session, suite.id)

    case_result = run_case(session, StubRunner(), run.id, cases[0])
    trace = get_trace(session, case_result.id)

    assert trace.input_tokens == 10
    assert trace.output_tokens == 5
