import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import Column, ForeignKey, JSON, String
from sqlmodel import Field, SQLModel


def uuid4_str() -> str:
    return str(uuid.uuid4())


class RunStatus(str, Enum):
    pending = "pending"
    running = "running"
    done = "done"
    failed = "failed"


class Suite(SQLModel, table=True):
    id: str = Field(default_factory=uuid4_str, primary_key=True)
    name: str
    description: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Case(SQLModel, table=True):
    __tablename__ = "case"

    id: str = Field(default_factory=uuid4_str, primary_key=True)
    suite_id: str = Field(foreign_key="suite.id")
    title: str = ""
    input: str
    context: str | None = None
    expected_behavior: str
    # list[{id, name, description, weight}] — stored as JSON
    rubric: list[dict[str, Any]] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Run(SQLModel, table=True):
    id: str = Field(default_factory=uuid4_str, primary_key=True)
    suite_id: str = Field(foreign_key="suite.id")
    status: RunStatus = RunStatus.pending
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CaseResult(SQLModel, table=True):
    __tablename__ = "case_result"

    id: str = Field(default_factory=uuid4_str, primary_key=True)
    run_id: str = Field(foreign_key="run.id")
    case_id: str = Field(foreign_key="case.id")
    passed: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Trace(SQLModel, table=True):
    id: str = Field(default_factory=uuid4_str, primary_key=True)
    case_result_id: str = Field(
        sa_column=Column(String, ForeignKey("case_result.id"), unique=True)
    )
    # list[{type, timestamp, content}] — stored as JSON
    events: list[dict[str, Any]] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    latency_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0


class RubricScore(SQLModel, table=True):
    __tablename__ = "rubric_score"

    id: str = Field(default_factory=uuid4_str, primary_key=True)
    case_result_id: str = Field(foreign_key="case_result.id")
    dimension_id: str
    dimension_name: str = ""
    score: float  # 0.0-1.0
    justification: str = ""


class RubricDimension(SQLModel):
    """Non-table value object for one rubric scoring axis."""

    id: str
    name: str
    description: str
    weight: float  # 0.0-1.0; weights should sum to 1.0
