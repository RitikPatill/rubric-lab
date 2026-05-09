import pytest
from sqlmodel import Session, SQLModel, create_engine

import rubriclab.models as _  # noqa: F401 — registers all table metadata


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
