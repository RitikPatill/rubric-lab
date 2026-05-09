from sqlmodel import Session, select

from .models import Case, Suite

SUITE_NAME = "Research Agent v1"

_CASES = [
    # Case 1: Factual — basic
    {
        "title": "Factual — capital of France",
        "input": "What is the capital of France?",
        "expected_behavior": "Responds with 'Paris' concisely.",
        "rubric": [
            {
                "id": "correctness",
                "name": "Correctness",
                "description": "Answer is factually accurate",
                "weight": 1.0,
            },
        ],
    },
    # Case 2: Factual — multi-part
    {
        "title": "Factual — telephone inventor",
        "input": "Who invented the telephone and in what year?",
        "expected_behavior": "States Alexander Graham Bell invented the telephone in 1876.",
        "rubric": [
            {
                "id": "correctness",
                "name": "Correctness",
                "description": "Person and year are factually accurate",
                "weight": 0.6,
            },
            {
                "id": "completeness",
                "name": "Completeness",
                "description": "Both inventor name and year are included",
                "weight": 0.4,
            },
        ],
    },
    # Case 3: Tool-use — calculator
    {
        "title": "Tool-use — calculator",
        "input": "What is 1,234 × 5,678? Use the calculator tool.",
        "expected_behavior": "Uses the calculator tool and returns 7,006,652.",
        "rubric": [
            {
                "id": "correctness",
                "name": "Correctness",
                "description": "Numeric result is correct",
                "weight": 0.5,
            },
            {
                "id": "tool_use_efficiency",
                "name": "Tool-use Efficiency",
                "description": "Agent used the calculator tool without unnecessary calls",
                "weight": 0.5,
            },
        ],
    },
    # Case 4: Tool-use — web search
    {
        "title": "Tool-use — web search",
        "input": "Search for the current population of Tokyo and report it.",
        "expected_behavior": "Uses web_search tool and reports a plausible current population for Tokyo.",
        "rubric": [
            {
                "id": "tool_use_efficiency",
                "name": "Tool-use Efficiency",
                "description": "Agent used the web search tool correctly",
                "weight": 0.5,
            },
            {
                "id": "correctness",
                "name": "Correctness",
                "description": "Reported figure is plausible for Tokyo's population",
                "weight": 0.3,
            },
            {
                "id": "format_adherence",
                "name": "Format Adherence",
                "description": "Response is clearly formatted and attributable",
                "weight": 0.2,
            },
        ],
    },
    # Case 5: Tool-use — chained
    {
        "title": "Tool-use — chained tools",
        "input": "Find the boiling point of water in Celsius via search, then convert it to Fahrenheit.",
        "expected_behavior": "Uses web_search to find 100°C, then uses calculator or reasoning to return 212°F.",
        "rubric": [
            {
                "id": "tool_use_efficiency",
                "name": "Tool-use Efficiency",
                "description": "Agent chained tools without unnecessary calls",
                "weight": 0.4,
            },
            {
                "id": "correctness",
                "name": "Correctness",
                "description": "Final answer of 212°F is correct",
                "weight": 0.4,
            },
            {
                "id": "reasoning_quality",
                "name": "Reasoning Quality",
                "description": "Conversion reasoning is shown and correct",
                "weight": 0.2,
            },
        ],
    },
    # Case 6: Format — bullet list
    {
        "title": "Format — bullet list",
        "input": "List exactly 5 programming languages and their primary use cases as a markdown bullet list.",
        "expected_behavior": "Returns exactly 5 markdown bullet points, each naming a language and its primary use case.",
        "rubric": [
            {
                "id": "format_adherence",
                "name": "Format Adherence",
                "description": "Output is a markdown bullet list with exactly 5 items",
                "weight": 0.5,
            },
            {
                "id": "completeness",
                "name": "Completeness",
                "description": "Each item includes both a language name and its use case",
                "weight": 0.3,
            },
            {
                "id": "correctness",
                "name": "Correctness",
                "description": "Languages and use cases are accurate",
                "weight": 0.2,
            },
        ],
    },
    # Case 7: Format — JSON
    {
        "title": "Format — JSON output",
        "input": "Return a JSON object with keys `company`, `founded_year`, `headquarters` for Apple Inc. Output only the JSON.",
        "expected_behavior": '{"company": "Apple Inc.", "founded_year": 1976, "headquarters": "Cupertino, CA"}',
        "rubric": [
            {
                "id": "format_adherence",
                "name": "Format Adherence",
                "description": "Output is valid JSON with exactly the three required keys",
                "weight": 0.6,
            },
            {
                "id": "correctness",
                "name": "Correctness",
                "description": "Values are factually accurate for Apple Inc.",
                "weight": 0.4,
            },
        ],
    },
    # Case 8: Reasoning
    {
        "title": "Reasoning — average speed",
        "input": "A car travels 150 miles in 2.5 hours. What is its average speed in mph? Show your reasoning.",
        "expected_behavior": "Shows reasoning (150 ÷ 2.5) and returns 60 mph.",
        "rubric": [
            {
                "id": "correctness",
                "name": "Correctness",
                "description": "Final answer is 60 mph",
                "weight": 0.5,
            },
            {
                "id": "reasoning_quality",
                "name": "Reasoning Quality",
                "description": "Calculation steps are shown and correct",
                "weight": 0.5,
            },
        ],
    },
]


def seed_demo_suite(session: Session) -> Suite:
    """Populate the demo suite idempotently. Returns the (possibly existing) Suite."""
    existing = session.exec(select(Suite).where(Suite.name == SUITE_NAME)).first()
    if existing:
        return existing

    suite = Suite(name=SUITE_NAME, description="Demo suite for the built-in research agent.")
    session.add(suite)
    session.commit()
    session.refresh(suite)

    for c in _CASES:
        case = Case(suite_id=suite.id, **c)
        session.add(case)
    session.commit()

    return suite


# Public aliases for plan / test compatibility
seed_demo = seed_demo_suite
seed_if_empty = seed_demo_suite
