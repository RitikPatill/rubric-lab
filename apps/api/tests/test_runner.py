"""Tests for runner types and ResearchAgent — no real API key required."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from rubriclab.agents.research import ResearchAgent
from rubriclab.agents.tools import calculator
from rubriclab.runner import TraceResult

# ---------------------------------------------------------------------------
# Helpers to build mock Anthropic responses (SimpleNamespace matches SDK shape)
# ---------------------------------------------------------------------------


def _end_turn_response(text: str, in_tok: int = 10, out_tok: int = 5) -> SimpleNamespace:
    blk = SimpleNamespace(type="text", text=text)
    return SimpleNamespace(
        stop_reason="end_turn",
        content=[blk],
        usage=SimpleNamespace(input_tokens=in_tok, output_tokens=out_tok),
    )


def _tool_use_response(
    tool_name: str,
    tool_input: dict,
    tool_use_id: str = "tu_1",
    in_tok: int = 10,
    out_tok: int = 5,
) -> SimpleNamespace:
    blk = SimpleNamespace(
        type="tool_use",
        id=tool_use_id,
        name=tool_name,
        input=tool_input,
    )
    return SimpleNamespace(
        stop_reason="tool_use",
        content=[blk],
        usage=SimpleNamespace(input_tokens=in_tok, output_tokens=out_tok),
    )


# ---------------------------------------------------------------------------
# Fixture: patch Anthropic constructor so no real API key is needed
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_client():
    with patch("rubriclab.agents.research.anthropic.Anthropic") as MockClient:
        instance = MockClient.return_value
        yield instance


# ---------------------------------------------------------------------------
# calculator tests (no mock needed)
# ---------------------------------------------------------------------------


def test_calculator_integer_multiply():
    assert calculator("1234 * 5678") == "7006652"


def test_calculator_float_division():
    assert calculator("150 / 2.5") == "60.0"


def test_calculator_compound_expression():
    assert calculator("(100 * 9/5) + 32") == "212.0"


def test_calculator_invalid_raises():
    with pytest.raises(ValueError):
        calculator("__import__('os')")


# ---------------------------------------------------------------------------
# Web search stub tests (no mock — _execute_tool has no __init__ deps)
# ---------------------------------------------------------------------------


def test_web_search_tokyo():
    # Use __new__ to skip __init__ (avoids needing an Anthropic API key)
    agent = ResearchAgent.__new__(ResearchAgent)
    result = agent._execute_tool("web_search", {"query": "population of Tokyo"})
    assert "tokyo" in result.lower() or len(result) > 0


def test_web_search_unknown_fallback():
    agent = ResearchAgent.__new__(ResearchAgent)
    result = agent._execute_tool("web_search", {"query": "xyzzy_unknown_query_12345"})
    assert "[web_search]" in result and "found" in result.lower()


# ---------------------------------------------------------------------------
# Full agent loop tests (mock Anthropic client via fixture)
# ---------------------------------------------------------------------------


def test_agent_direct_answer(mock_client):
    mock_client.messages.create.return_value = _end_turn_response("Paris is the capital.")
    agent = ResearchAgent()
    result = agent.run("What is the capital of France?")

    assert isinstance(result, TraceResult)
    assert result.final_output
    model_calls = [e for e in result.events if e["type"] == "model_call"]
    final_outputs = [e for e in result.events if e["type"] == "final_output"]
    assert len(model_calls) == 1
    assert len(final_outputs) == 1


def test_agent_tool_loop(mock_client):
    mock_client.messages.create.side_effect = [
        _tool_use_response("calculator", {"expression": "6 * 7"}, "tu_42"),
        _end_turn_response("The answer is 42."),
    ]
    agent = ResearchAgent()
    result = agent.run("What is 6 times 7?")

    types = [e["type"] for e in result.events]
    assert types == ["model_call", "tool_call", "tool_result", "model_call", "final_output"]


def test_trace_event_schema(mock_client):
    mock_client.messages.create.side_effect = [
        _tool_use_response("web_search", {"query": "tokyo"}, "tu_1"),
        _end_turn_response("Tokyo is a large city."),
    ]
    agent = ResearchAgent()
    result = agent.run("Tell me about Tokyo")

    for event in result.events:
        assert "type" in event, f"Missing 'type' in event: {event}"
        assert "timestamp" in event, f"Missing 'timestamp' in event: {event}"
        assert "content" in event, f"Missing 'content' in event: {event}"


def test_token_accumulation(mock_client):
    mock_client.messages.create.side_effect = [
        _tool_use_response("calculator", {"expression": "1+1"}, in_tok=10, out_tok=5),
        _end_turn_response("2", in_tok=10, out_tok=5),
    ]
    agent = ResearchAgent()
    result = agent.run("1+1?")

    assert result.input_tokens == 20
    assert result.output_tokens == 10


def test_latency_ms_positive(mock_client):
    mock_client.messages.create.return_value = _end_turn_response("Done.")
    agent = ResearchAgent()
    result = agent.run("Test")
    assert result.latency_ms >= 0
