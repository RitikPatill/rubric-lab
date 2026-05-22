"""Tests for ResearchAgent with mocked Anthropic client."""
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from rubriclab.runner import TraceResult
from rubriclab.agents.research import ResearchAgent
from rubriclab.agents.tools import calculator


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _text_msg(text, input_tokens=10, output_tokens=20):
    blk = SimpleNamespace(type="text", text=text)
    return SimpleNamespace(
        stop_reason="end_turn",
        content=[blk],
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens),
    )


def _tool_msg(name, tool_input, tool_use_id="tu_1", input_tokens=10, output_tokens=20):
    blk = SimpleNamespace(type="tool_use", name=name, input=tool_input, id=tool_use_id)
    return SimpleNamespace(
        stop_reason="tool_use",
        content=[blk],
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens),
    )


def _make_agent(*responses):
    """Build a ResearchAgent with a mock Anthropic client returning *responses in order."""
    with patch("rubriclab.agents.research.anthropic.Anthropic") as MockCls:
        MockCls.return_value.messages.create.side_effect = list(responses)
        return ResearchAgent()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_run_result_fields():
    agent = _make_agent(_text_msg("Hello!"))
    result = agent.run("Say hello")
    assert isinstance(result, TraceResult)
    assert isinstance(result.events, list)
    assert isinstance(result.final_output, str)
    assert result.latency_ms >= 0
    assert result.input_tokens > 0
    assert result.output_tokens > 0


def test_events_have_required_keys():
    agent = _make_agent(_text_msg("Hi"))
    result = agent.run("Hi there")
    for event in result.events:
        assert "type" in event
        assert "timestamp" in event
        assert "content" in event


def test_calculator_tool_use():
    agent = _make_agent(
        _tool_msg("calculator", {"expression": "6*7"}),
        _text_msg("42"),
    )
    result = agent.run("What is 6 times 7?")
    tool_calls = [e for e in result.events if e["type"] == "tool_call"]
    tool_results = [e for e in result.events if e["type"] == "tool_result"]
    assert len(tool_calls) == 1
    assert tool_calls[0]["content"]["tool_name"] == "calculator"
    assert len(tool_results) == 1
    assert result.final_output == "42"


def test_web_search_tool_use():
    agent = _make_agent(
        _tool_msg("web_search", {"query": "capital of france"}),
        _text_msg("Paris"),
    )
    result = agent.run("What is the capital of France?")
    tool_calls = [e for e in result.events if e["type"] == "tool_call"]
    assert len(tool_calls) == 1
    assert tool_calls[0]["content"]["tool_name"] == "web_search"
    assert result.final_output == "Paris"


def test_token_accumulation():
    agent = _make_agent(
        _tool_msg("calculator", {"expression": "1+1"}, input_tokens=5, output_tokens=5),
        _text_msg("2", input_tokens=5, output_tokens=5),
    )
    result = agent.run("1+1?")
    assert result.input_tokens == 10
    assert result.output_tokens == 10


def test_calculator_arithmetic():
    assert calculator("1234 * 5678") == "7006652"


def test_web_search_stub_tokyo():
    agent = ResearchAgent.__new__(ResearchAgent)
    result = agent._execute_tool("web_search", {"query": "population of tokyo"})
    assert "37.4 million" in result or "tokyo" in result.lower()


def test_calculator_invalid_raises():
    with pytest.raises(ValueError):
        calculator("__import__('os')")
