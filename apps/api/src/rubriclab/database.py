import os
from collections.abc import Generator
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/rubriclab.db")

# Ensure the data directory exists for SQLite file databases
Path("data").mkdir(exist_ok=True)

_connect_args: dict = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, echo=False, connect_args=_connect_args)


def get_engine():
    return engine


def create_tables() -> None:
    SQLModel.metadata.create_all(engine)


# Alias for plan compatibility
create_db_and_tables = create_tables


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
