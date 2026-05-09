from unittest.mock import MagicMock

import pytest

from rubriclab.runner import AgentResult
from rubriclab.agents.research import ResearchAgent, _calculator, _web_search


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _text_msg(text, input_tokens=10, output_tokens=20):
    """Simulate a final text response from the model."""
    msg = MagicMock()
    msg.stop_reason = "end_turn"
    blk = MagicMock()
    blk.type = "text"
    blk.text = text
    msg.content = [blk]
    msg.usage.input_tokens = input_tokens
    msg.usage.output_tokens = output_tokens
    return msg


def _tool_msg(name, tool_input, tool_use_id="tu_1", input_tokens=10, output_tokens=20):
    """Simulate a tool-use response from the model."""
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


def _make_agent(*responses):
    """Build a ResearchAgent with a mock client that returns *responses in order."""
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = list(responses)
    return ResearchAgent(client=mock_client)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_run_result_fields():
    agent = _make_agent(_text_msg("Hello!"))
    result = agent.run("Say hello")
    assert isinstance(result, AgentResult)
    assert isinstance(result.events, list)
    assert isinstance(result.output, str)
    assert result.latency_ms >= 0
    assert result.input_tokens > 0
    assert result.output_tokens > 0


def test_events_include_user_message():
    agent = _make_agent(_text_msg("Hi"))
    result = agent.run("Hi there")
    assert result.events[0]["type"] == "user_message"


def test_calculator_tool_use():
    agent = _make_agent(
        _tool_msg("calculator", {"expression": "6*7"}),
        _text_msg("42"),
    )
    result = agent.run("What is 6 times 7?")

    tool_calls = [e for e in result.events if e["type"] == "tool_call"]
    tool_results = [e for e in result.events if e["type"] == "tool_result"]

    assert len(tool_calls) == 1
    assert tool_calls[0]["tool_name"] == "calculator"
    assert len(tool_results) == 1
    assert result.output == "42"


def test_web_search_tool_use():
    agent = _make_agent(
        _tool_msg("web_search", {"query": "capital of france"}),
        _text_msg("Paris"),
    )
    result = agent.run("What is the capital of France?")

    tool_calls = [e for e in result.events if e["type"] == "tool_call"]
    tool_results = [e for e in result.events if e["type"] == "tool_result"]

    assert len(tool_calls) == 1
    assert tool_calls[0]["tool_name"] == "web_search"
    assert len(tool_results) == 1
    assert result.output == "Paris"


def test_token_accumulation():
    agent = _make_agent(
        _tool_msg("calculator", {"expression": "1+1"}, input_tokens=5, output_tokens=5),
        _text_msg("2", input_tokens=5, output_tokens=5),
    )
    result = agent.run("1+1?")
    assert result.input_tokens == 10
    assert result.output_tokens == 10


def test_calculator_stub_arithmetic():
    assert _calculator("1234 * 5678") == "7006652"


def test_web_search_stub_tokyo():
    result = _web_search("population of tokyo")
    assert "Tokyo" in result


def test_calculator_blocks_eval_injection():
    with pytest.raises(ValueError):
        _calculator("__import__('os').system('ls')")
