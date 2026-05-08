from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

import rubriclab.models  # noqa: F401 — register all SQLModel tables with metadata
from rubriclab.database import create_tables, engine
from rubriclab.seed import seed_demo_suite


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    with Session(engine) as session:
        seed_demo_suite(session)
    yield


app = FastAPI(title="RubricLab API", version="0.1.0", lifespan=lifespan)

# WARNING: lock down before production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict:
    return {"service": "rubriclab-api", "version": "0.1.0"}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
