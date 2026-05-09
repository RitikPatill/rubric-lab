from sqlmodel import Session, select

from .models import Case, CaseResult, Run, RubricScore, Suite, Trace


# --- Suite ---

def create_suite(session: Session, suite: Suite) -> Suite:
    session.add(suite)
    session.commit()
    session.refresh(suite)
    return suite


def get_suite(session: Session, suite_id: str) -> Suite | None:
    return session.get(Suite, suite_id)


def list_suites(session: Session) -> list[Suite]:
    return list(session.exec(select(Suite)).all())


# --- Case ---

def create_case(session: Session, case: Case) -> Case:
    session.add(case)
    session.commit()
    session.refresh(case)
    return case


def get_case(session: Session, case_id: str) -> Case | None:
    return session.get(Case, case_id)


def list_cases(session: Session, suite_id: str) -> list[Case]:
    return list(session.exec(select(Case).where(Case.suite_id == suite_id)).all())


get_cases = list_cases


# --- Run ---

def create_run(session: Session, suite_id: str) -> Run:
    run = Run(suite_id=suite_id)
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def get_run(session: Session, run_id: str) -> Run | None:
    return session.get(Run, run_id)


def list_runs(session: Session, suite_id: str) -> list[Run]:
    return list(session.exec(select(Run).where(Run.suite_id == suite_id)).all())


get_runs = list_runs


# --- CaseResult ---

def create_case_result(
    session: Session,
    run_id: str,
    case_id: str,
    passed: bool,
    created_at=None,
) -> CaseResult:
    obj = CaseResult(run_id=run_id, case_id=case_id, passed=passed)
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


def list_case_results(session: Session, run_id: str) -> list[CaseResult]:
    return list(session.exec(select(CaseResult).where(CaseResult.run_id == run_id)).all())


get_run_results = list_case_results


# --- Trace ---

def get_trace(session: Session, case_result_id: str) -> Trace | None:
    return session.exec(select(Trace).where(Trace.case_result_id == case_result_id)).first()


def create_trace(
    session: Session,
    case_result_id: str,
    events: list[dict],
    *,
    latency_ms: int = 0,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> Trace:
    trace = Trace(
        case_result_id=case_result_id,
        events=events,
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
    session.add(trace)
    session.commit()
    session.refresh(trace)
    return trace


# --- RubricScore ---

def create_rubric_score(
    session: Session,
    case_result_id: str,
    dimension_id: str,
    score: float,
    justification: str,
    dimension_name: str = "",
) -> RubricScore:
    obj = RubricScore(
        case_result_id=case_result_id,
        dimension_id=dimension_id,
        dimension_name=dimension_name or dimension_id,
        score=score,
        justification=justification,
    )
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


def list_scores(session: Session, case_result_id: str) -> list[RubricScore]:
    return list(
        session.exec(select(RubricScore).where(RubricScore.case_result_id == case_result_id)).all()
    )
