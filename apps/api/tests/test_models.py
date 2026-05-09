import pytest
from sqlalchemy import text
from sqlmodel import Session, select

from rubriclab.models import Case, CaseResult, Run, RunStatus, Suite, Trace
from rubriclab.repository import create_run, get_run, list_cases, list_suites
from rubriclab.seed import seed_demo_suite


# ── Plan M2 required tests ────────────────────────────────────────────────────


def test_tables_created(session: Session):
    result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
    table_names = {row[0] for row in result}
    assert {"suite", "case", "run", "case_result", "trace", "rubric_score"} <= table_names


def test_seed_returns_suite(session: Session):
    suite = seed_demo_suite(session)
    assert suite.name == "Research Agent v1"


def test_seed_creates_8_cases(session: Session):
    suite = seed_demo_suite(session)
    assert len(list_cases(session, suite.id)) == 8


def test_seed_idempotent(session: Session):
    seed_demo_suite(session)
    seed_demo_suite(session)
    suites = list_suites(session)
    assert len([s for s in suites if s.name == "Research Agent v1"]) == 1


def test_rubric_weights_sum_to_1(session: Session):
    suite = seed_demo_suite(session)
    for case in list_cases(session, suite.id):
        total = sum(d["weight"] for d in case.rubric)
        assert total == pytest.approx(1.0), (
            f"Case '{case.input[:40]}' weights sum to {total}"
        )


def test_create_run(session: Session):
    suite = seed_demo_suite(session)
    run = create_run(session, suite.id)
    assert get_run(session, run.id) is not None


# ── Additional coverage ───────────────────────────────────────────────────────


def test_suite_roundtrip(session: Session):
    suite = Suite(name="Test Suite", description="A test suite")
    session.add(suite)
    session.commit()
    fetched = session.get(Suite, suite.id)
    assert fetched is not None
    assert fetched.name == "Test Suite"


def test_case_rubric_is_list(session: Session):
    suite = Suite(name="S")
    session.add(suite)
    session.commit()
    rubric = [
        {"id": "correctness", "name": "Correctness", "description": "OK", "weight": 0.6},
        {"id": "format", "name": "Format", "description": "Fmt", "weight": 0.4},
    ]
    case = Case(suite_id=suite.id, title="T", input="Q", expected_behavior="A", rubric=rubric)
    session.add(case)
    session.commit()
    fetched = session.get(Case, case.id)
    assert isinstance(fetched.rubric, list)
    assert fetched.rubric[0]["id"] == "correctness"


def test_run_status_default(session: Session):
    suite = Suite(name="S2")
    session.add(suite)
    session.commit()
    run = Run(suite_id=suite.id)
    session.add(run)
    session.commit()
    assert run.status == RunStatus.pending


def test_trace_unique_constraint(session: Session):
    from sqlalchemy.exc import IntegrityError

    suite = Suite(name="S3")
    session.add(suite)
    session.commit()
    case = Case(suite_id=suite.id, input="Q", expected_behavior="A", rubric=[])
    session.add(case)
    run = Run(suite_id=suite.id)
    session.add(run)
    session.commit()
    cr = CaseResult(run_id=run.id, case_id=case.id)
    session.add(cr)
    session.commit()

    t1 = Trace(case_result_id=cr.id, events=[])
    session.add(t1)
    session.commit()

    t2 = Trace(case_result_id=cr.id, events=[])
    session.add(t2)
    with pytest.raises(IntegrityError):
        session.commit()


def test_get_suite_none_for_missing(session: Session):
    assert session.get(Suite, "nonexistent") is None
