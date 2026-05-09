"""
LLM-as-judge engine for RubricLab M4.

Takes a TraceResult + rubric dimensions, calls Claude via tool-use to produce
per-dimension numeric scores (0.0-1.0) and one-sentence justifications,
then computes a weighted aggregate score.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import anthropic

if TYPE_CHECKING:
    from .runner import TraceResult

logger = logging.getLogger(__name__)

SCORE_TOOL = {
    "name": "submit_scores",
    "description": "Record per-dimension rubric scores.",
    "input_schema": {
        "type": "object",
        "properties": {
            "scores": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "dimension_id": {"type": "string"},
                        "score": {"type": "number", "minimum": 0, "maximum": 1},
                        "justification": {"type": "string"},
                    },
                    "required": ["dimension_id", "score", "justification"],
                },
            }
        },
        "required": ["scores"],
    },
}


@dataclass
class DimensionScore:
    dimension_id: str
    dimension_name: str
    score: float         # 0.0–1.0
    justification: str


@dataclass
class JudgeResult:
    dimension_scores: list[DimensionScore]
    weighted_score: float   # weighted average, 0.0–1.0
    passed: bool            # weighted_score >= pass_threshold


class JudgeEngine:
    def __init__(
        self,
        model: str = "claude-haiku-4-5-20251001",
        api_key: str | None = None,
        pass_threshold: float = 0.7,
    ) -> None:
        self._model = model
        self._pass_threshold = pass_threshold
        self._client = anthropic.Anthropic(api_key=api_key)

    def score(
        self,
        trace_result: TraceResult,
        rubric: list[dict],
        expected_behavior: str,
        case_input: str,
    ) -> JudgeResult:
        """Call Claude once to score all rubric dimensions. Returns a JudgeResult."""
        if not rubric:
            return JudgeResult(dimension_scores=[], weighted_score=0.0, passed=False)

        user_prompt = self._build_user_prompt(case_input, expected_behavior, rubric, trace_result)
        dimension_scores = self._call_claude(user_prompt, rubric)
        weighted = self._weighted_score(dimension_scores, rubric)
        return JudgeResult(
            dimension_scores=dimension_scores,
            weighted_score=weighted,
            passed=weighted >= self._pass_threshold,
        )

    def _build_user_prompt(
        self,
        case_input: str,
        expected_behavior: str,
        rubric: list[dict],
        trace_result: TraceResult,
    ) -> str:
        lines: list[str] = []

        lines.append("## Input")
        lines.append(case_input or "(not provided)")
        lines.append("")

        lines.append("## Expected Behavior")
        lines.append(expected_behavior)
        lines.append("")

        lines.append("## Rubric Dimensions")
        for dim in rubric:
            lines.append(
                f"  - id={dim.get('id', '')}  name={dim.get('name', '')}  "
                f"weight={dim.get('weight', 1.0)}  desc={dim.get('description', '')}"
            )
        lines.append("")

        lines.append("## Agent Final Output")
        lines.append(trace_result.final_output)
        lines.append("")

        tool_names = [
            e["content"].get("tool_name", "")
            for e in trace_result.events
            if e.get("type") == "tool_call"
        ]
        model_call_count = sum(1 for e in trace_result.events if e.get("type") == "model_call")
        lines.append("## Trace Summary")
        lines.append(f"  model calls: {model_call_count}")
        lines.append(f"  tools used: {tool_names or 'none'}")

        return "\n".join(lines)

    def _call_claude(self, user_prompt: str, rubric: list[dict]) -> list[DimensionScore]:
        try:
            resp = self._client.messages.create(
                model=self._model,
                max_tokens=1024,
                tools=[SCORE_TOOL],
                tool_choice={"type": "tool", "name": "submit_scores"},
                messages=[{"role": "user", "content": user_prompt}],
            )
            block = resp.content[0]
            # Tool-use response (production): ToolUseBlock has .input dict
            # Text response (tests/fallback): SimpleNamespace has .text string
            if hasattr(block, "input"):
                raw_scores = block.input.get("scores", [])
            else:
                raw_scores = json.loads(block.text).get("scores", [])
        except Exception as exc:
            logger.warning("JudgeEngine Claude call failed: %s", exc)
            raw_scores = []

        parsed_map: dict[str, dict] = {
            s["dimension_id"]: s for s in raw_scores if "dimension_id" in s
        }

        result: list[DimensionScore] = []
        for dim in rubric:
            dim_id = dim.get("id", "")
            dim_name = dim.get("name", dim_id)
            entry = parsed_map.get(dim_id, {})
            raw_score = entry.get("score", 0.0)
            clamped = max(0.0, min(1.0, float(raw_score)))
            result.append(
                DimensionScore(
                    dimension_id=dim_id,
                    dimension_name=dim_name,
                    score=clamped,
                    justification=entry.get("justification", ""),
                )
            )
        return result

    def _weighted_score(self, scores: list[DimensionScore], rubric: list[dict]) -> float:
        weights = [dim.get("weight", 1.0) for dim in rubric]
        total = sum(weights)
        if total == 0.0:
            return 0.0
        return sum(s.score * w for s, w in zip(scores, weights)) / total
