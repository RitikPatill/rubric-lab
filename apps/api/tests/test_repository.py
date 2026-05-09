from rubriclab.repository import create_run, get_case, get_cases, get_run, get_runs, list_suites
from rubriclab.seed import seed_demo_suite


def test_seed_creates_suite_and_cases(session):
    seed_demo_suite(session)
    session.commit()

    suites = list_suites(session)
    assert len(suites) == 1
    assert suites[0].name == "Research Agent v1"

    cases = get_cases(session, suites[0].id)
    assert len(cases) == 8


def test_seed_is_idempotent(session):
    seed_demo_suite(session)
    session.commit()
    seed_demo_suite(session)
    session.commit()

    assert len(list_suites(session)) == 1
    suite_id = list_suites(session)[0].id
    assert len(get_cases(session, suite_id)) == 8


def test_create_and_get_run(session):
    seed_demo_suite(session)
    session.commit()

    suite_id = list_suites(session)[0].id
    run = create_run(session, suite_id)

    assert run.status == "pending"
    assert run.suite_id == suite_id

    fetched = get_run(session, run.id)
    assert fetched is not None
    assert fetched.id == run.id

    runs = get_runs(session, suite_id)
    assert len(runs) == 1
    assert runs[0].id == run.id


def test_get_case_returns_rubric(session):
    seed_demo_suite(session)
    session.commit()

    suite_id = list_suites(session)[0].id
    cases = get_cases(session, suite_id)
    assert len(cases) > 0

    for case in cases:
        fetched = get_case(session, case.id)
        assert fetched is not None
        assert isinstance(fetched.rubric, list)
        assert len(fetched.rubric) > 0
        for dim in fetched.rubric:
            assert "id" in dim
            assert "name" in dim
            assert "weight" in dim
