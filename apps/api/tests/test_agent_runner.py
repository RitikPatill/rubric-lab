"""Tests for M3: AgentRunner protocol, tool helpers, ResearchAgent, and run_case()."""
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import Session

from rubriclab.runner import TraceResult
from rubriclab.agents.tools import calculator, web_search
from rubriclab.agents.research import ResearchAgent
from rubriclab.models import Case, Suite
from rubriclab.repository import create_case, create_run, create_suite
from rubriclab.runner import run_case


# ---------------------------------------------------------------------------
# Tool tests (no mocking needed)
# ---------------------------------------------------------------------------


def test_calculator_basic():
    assert calculator("6 * 7") == "42"


def test_calculator_commas_and_multiply_symbol():
    assert calculator("1,234 × 5,678") == "7006652"


def test_calculator_rejects_non_arithmetic():
    with pytest.raises(ValueError):
        calculator("__import__('os')")


def test_web_search_canned_tokyo():
    result = web_search("population of Tokyo")
    assert result  # non-empty string


def test_web_search_catch_all():
    result = web_search("xyzzy_completely_unknown_query_99999")
    assert result  # catch-all fires, still non-empty


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _end_turn(text="Done.", input_tokens=10, output_tokens=20):
    msg = MagicMock()
    msg.stop_reason = "end_turn"
    blk = MagicMock()
    blk.type = "text"
    blk.text = text
    msg.content = [blk]
    msg.usage.input_tokens = input_tokens
    msg.usage.output_tokens = output_tokens
    return msg


def _tool_use_resp(name, tool_input, tool_use_id="tu_1", input_tokens=10, output_tokens=10):
    msg = MagicMock()
    msg.stop_reason = "tool_use"
    blk = MagicMock()
    blk.type = "tool_use"
    blk.name = name
    blk.input = tool_input
    blk.id = tool_use_id
    msg.content = [blk]
    msg.usage.input_tokens = input_tokens
    msg.usage.output_tokens = output_tokens
    return msg


# ---------------------------------------------------------------------------
# ResearchAgent with mocked client — happy path (no tool use)
# ---------------------------------------------------------------------------


def test_agent_no_tool_use():
    with patch("rubriclab.agents.research.anthropic.Anthropic") as MockClient:
        mock_client = MockClient.return_value
        mock_client.messages.create.return_value = _end_turn(
            "Hello world!", input_tokens=15, output_tokens=25
        )
        agent = ResearchAgent()
        trace = agent.run("Say hello")

    assert isinstance(trace, TraceResult)
    types = [e["type"] for e in trace.events]
    assert "model_call" in types
    assert "final_output" in types
    assert trace.final_output == "Hello world!"
    assert trace.input_tokens == 15
    assert trace.output_tokens == 25


# ---------------------------------------------------------------------------
# ResearchAgent with tool-use response — one tool call then end_turn
# ---------------------------------------------------------------------------


def test_agent_one_tool_round_trip():
    with patch("rubriclab.agents.research.anthropic.Anthropic") as MockClient:
        mock_client = MockClient.return_value
        mock_client.messages.create.side_effect = [
            _tool_use_resp("calculator", {"expression": "6*7"}, input_tokens=10, output_tokens=10),
            _end_turn("The answer is 42", input_tokens=10, output_tokens=10),
        ]
        agent = ResearchAgent()
        trace = agent.run("What is 6 times 7?")

    types = [e["type"] for e in trace.events]
    assert types == ["model_call", "tool_call", "tool_result", "model_call", "final_output"]
    assert trace.input_tokens == 20
    assert trace.output_tokens == 20
    assert trace.final_output == "The answer is 42"


# ---------------------------------------------------------------------------
# run_case integration test
# ---------------------------------------------------------------------------


def test_run_case_persists_to_db(session: Session):
    suite = create_suite(session, Suite(name="test-suite"))
    case = create_case(
        session,
        Case(
            suite_id=suite.id,
            input="What is 2+2?",
            expected_behavior="Should return 4.",
        ),
    )
    run = create_run(session, suite.id)

    fixed_trace = TraceResult(
        events=[
            {
                "type": "model_call",
                "timestamp": "2024-01-01T00:00:00+00:00",
                "stop_reason": "end_turn",
                "latency_ms": 50,
                "input_tokens": 5,
                "output_tokens": 5,
            },
            {
                "type": "final_output",
                "timestamp": "2024-01-01T00:00:00+00:00",
                "content": "4",
            },
        ],
        final_output="4",
        latency_ms=50,
        input_tokens=5,
        output_tokens=5,
    )

    mock_agent = MagicMock()
    mock_agent.run.return_value = fixed_trace

    case_result, trace = run_case(session, run.id, case, mock_agent)

    assert case_result.run_id == run.id
    assert case_result.case_id == case.id
    assert case_result.passed is False  # placeholder until M4 scoring

    assert trace.case_result_id == case_result.id
    assert trace.events == fixed_trace.events
    assert trace.input_tokens == 5
    assert trace.output_tokens == 5
    assert trace.latency_ms == 50
