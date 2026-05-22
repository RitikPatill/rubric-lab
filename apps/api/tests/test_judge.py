"""Tests for JudgeEngine — no real API key required."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from sqlmodel import Session, SQLModel, create_engine

from rubriclab.judge import DimensionScore, JudgeEngine, JudgeResult
from rubriclab.models import Case, Suite
from rubriclab.repository import create_case, create_run, create_suite, list_scores
from rubriclab.runner import TraceResult, run_case


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_trace(final_output: str = "ok", events=None) -> TraceResult:
    return TraceResult(
        events=events or [],
        final_output=final_output,
        latency_ms=10,
        input_tokens=5,
        output_tokens=5,
    )


def _submit_scores_response(scores: list[dict]) -> SimpleNamespace:
    """Build a mock Anthropic response containing a submit_scores tool_use block."""
    block = SimpleNamespace(type="tool_use", input={"scores": scores})
    return SimpleNamespace(content=[block])


RUBRIC_ONE = [
    {"id": "correctness", "name": "Correctness", "description": "Is it correct?", "weight": 1.0}
]
RUBRIC_TWO = [
    {"id": "correctness", "name": "Correctness", "description": "Is it correct?", "weight": 0.6},
    {"id": "efficiency", "name": "Efficiency", "description": "Is it efficient?", "weight": 0.4},
]


# ---------------------------------------------------------------------------
# Test 1: happy path — JudgeResult shape and scores field
# ---------------------------------------------------------------------------


def test_judge_returns_judge_result():
    raw = [{"dimension_id": "correctness", "score": 0.9, "justification": "Looks good."}]
    with patch("rubriclab.judge.anthropic.Anthropic") as MockCls:
        MockCls.return_value.messages.create.return_value = _submit_scores_response(raw)
        engine = JudgeEngine()
        result = engine.score("What is 2+2?", "Should answer 4.", RUBRIC_ONE, _make_trace("4"))

    assert isinstance(result, JudgeResult)
    assert len(result.scores) == 1
    assert result.scores[0].dimension_id == "correctness"
    assert result.scores[0].score == pytest.approx(0.9)
    assert result.scores[0].justification == "Looks good."
    assert result.weighted_score == pytest.approx(0.9)


# ---------------------------------------------------------------------------
# Test 2: weighted score math  0.6*1.0 + 0.4*0.5 = 0.8
# ---------------------------------------------------------------------------


def test_weighted_score_correct():
    raw = [
        {"dimension_id": "correctness", "score": 1.0, "justification": "Perfect."},
        {"dimension_id": "efficiency", "score": 0.5, "justification": "Acceptable."},
    ]
    with patch("rubriclab.judge.anthropic.Anthropic") as MockCls:
        MockCls.return_value.messages.create.return_value = _submit_scores_response(raw)
        engine = JudgeEngine()
        result = engine.score("q", "expected", RUBRIC_TWO, _make_trace("answer"))

    assert result.weighted_score == pytest.approx(0.8)


# ---------------------------------------------------------------------------
# Test 3: passes when weighted_score >= threshold
# ---------------------------------------------------------------------------


def test_pass_threshold_true():
    raw = [
        {"dimension_id": "correctness", "score": 1.0, "justification": "Perfect."},
        {"dimension_id": "efficiency", "score": 0.5, "justification": "Ok."},
    ]
    with patch("rubriclab.judge.anthropic.Anthropic") as MockCls:
        MockCls.return_value.messages.create.return_value = _submit_scores_response(raw)
        engine = JudgeEngine(pass_threshold=0.7)
        result = engine.score("q", "expected", RUBRIC_TWO, _make_trace("a"))

    assert result.passed is True  # weighted = 0.8 >= 0.7


# ---------------------------------------------------------------------------
# Test 4: fails when weighted_score < threshold
# ---------------------------------------------------------------------------


def test_pass_threshold_false():
    raw = [
        {"dimension_id": "correctness", "score": 0.5, "justification": "Partial."},
        {"dimension_id": "efficiency", "score": 0.5, "justification": "Partial."},
    ]
    with patch("rubriclab.judge.anthropic.Anthropic") as MockCls:
        MockCls.return_value.messages.create.return_value = _submit_scores_response(raw)
        engine = JudgeEngine(pass_threshold=0.7)
        result = engine.score("q", "expected", RUBRIC_TWO, _make_trace("a"))

    assert result.passed is False  # weighted = 0.5 < 0.7


# ---------------------------------------------------------------------------
# Test 5: weight normalisation — weights don't sum to 1.0
# ---------------------------------------------------------------------------


def test_score_clamps_weight_normalization():
    """Weights [2.0, 3.0] — normalised correctly: 1.0*(2/5) + 0.0*(3/5) = 0.4"""
    rubric = [
        {"id": "a", "name": "A", "description": "", "weight": 2.0},
        {"id": "b", "name": "B", "description": "", "weight": 3.0},
    ]
    raw = [
        {"dimension_id": "a", "score": 1.0, "justification": "Good."},
        {"dimension_id": "b", "score": 0.0, "justification": "Bad."},
    ]
    with patch("rubriclab.judge.anthropic.Anthropic") as MockCls:
        MockCls.return_value.messages.create.return_value = _submit_scores_response(raw)
        engine = JudgeEngine()
        result = engine.score("q", "expected", rubric, _make_trace("a"))

    assert result.weighted_score == pytest.approx(0.4)


# ---------------------------------------------------------------------------
# Test 6: integration — run_case with FakeJudge persists RubricScore rows
# ---------------------------------------------------------------------------


def test_run_case_with_judge():
    """FakeJudge (no mock) — assert CaseResult.passed and RubricScore rows persisted."""
    db_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(db_engine)

    class FakeRunner:
        def run(self, input, context=None):
            return TraceResult(
                events=[],
                final_output="Paris",
                latency_ms=1,
                input_tokens=1,
                output_tokens=1,
            )

    class FakeJudge:
        def score(self, case_input, expected_behavior, rubric, trace_result):
            return JudgeResult(
                scores=[
                    DimensionScore(
                        dimension_id="correctness",
                        dimension_name="Correctness",
                        score=1.0,
                        justification="Correct.",
                    )
                ],
                weighted_score=1.0,
                passed=True,
            )

    with Session(db_engine) as session:
        suite = create_suite(session, Suite(name="Test Suite"))
        case = create_case(
            session,
            Case(
                suite_id=suite.id,
                input="Capital of France?",
                expected_behavior="Paris",
                rubric=[
                    {"id": "correctness", "name": "Correctness", "description": "", "weight": 1.0}
                ],
            ),
        )
        run = create_run(session, suite.id)
        case_result, _trace = run_case(session, run.id, case, FakeRunner(), judge=FakeJudge())

        assert case_result.passed is True
        scores = list_scores(session, case_result.id)
        assert len(scores) == 1
        assert scores[0].dimension_id == "correctness"
        assert scores[0].dimension_name == "Correctness"
        assert scores[0].score == pytest.approx(1.0)
