from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="RubricLab API", version="0.1.0")

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
