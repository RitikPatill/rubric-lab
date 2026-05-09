import os

from sqlmodel import Session, SQLModel, create_engine

import rubriclab.models as _  # noqa: F401 — registers all table metadata

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./rubriclab.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def init_db() -> None:
    """Create all tables if they don't exist."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI dependency that yields a database session."""
    with Session(engine) as session:
        yield session
