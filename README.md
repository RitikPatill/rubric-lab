# RubricLab

> **Evaluation harness for AI agents.** Define structured test suites with rubrics, run your agent against them, get LLM-as-judge scores, inspect full execution traces, and diff runs over time to catch regressions.

![Status](https://img.shields.io/badge/status-alpha-orange)
![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.12-blue)
![Next.js](https://img.shields.io/badge/next.js-15-black)

> Screenshot coming in M8

---

## What is RubricLab?

Building an agent is easy. Knowing whether yesterday's prompt tweak made it *better or worse* is hard.

Most teams ship agents with vibes-based testing — a few manual prompts, no structured rubric, no regression catching. RubricLab is the missing dev-loop tool: write test cases once, score every change automatically, and see exactly where behavior drifted.

### What works today (M2)

**M1 — scaffold**

- Monorepo scaffold: `apps/api` (FastAPI), `apps/web` (Next.js 15), `packages/shared` TypeScript types
- FastAPI skeleton boots at `localhost:8000`; `GET /` and `GET /health` are live
- Next.js 15 app scaffold at `localhost:3000`
- Shared TypeScript domain types: `Suite`, `Case`, `Run`, `CaseResult`, `Trace`, `TraceEvent`, `RubricDimension`, `RubricScore` (see `packages/shared/src/index.ts`)
- Dev tooling configured: uv + ruff for Python, pnpm + prettier + eslint for JS/TS
- Docker Compose stub wires both services with a named SQLite volume
- MIT license, `.gitignore`, `.prettierrc`

**M2 — data model + storage**

- SQLModel table definitions for all six core entities: `Suite`, `Case`, `Run`, `CaseResult`, `Trace`, `RubricScore` (`apps/api/src/rubriclab/models.py`)
- SQLite bootstrap: `create_tables()` runs on startup; database file at `data/rubriclab.db`, configurable via `DATABASE_URL` env var (`apps/api/src/rubriclab/database.py`)
- Repository layer: CRUD helpers for every entity — `create_suite`, `list_cases`, `create_run`, `create_trace`, `create_rubric_score`, and more (`apps/api/src/rubriclab/repository.py`)
- Demo suite seeded on first boot: **"Research Agent v1"** with 8 cases spanning factual, tool-use, format, and reasoning categories; seed is idempotent (`apps/api/src/rubriclab/seed.py`)
- Test suite covering model round-trips and repository integration (`apps/api/tests/`)

### Planned

- **Agent runner** — pluggable interface (`run(input) -> trace`) that executes your agent and captures the full trace: model calls, tool calls, intermediate messages, final output, latency, token usage
- **LLM-as-judge engine** — Anthropic-powered judge scores each trace against the rubric and emits per-dimension scores + written justification
- **Dashboard** — Next.js UI to browse suites, trigger runs, view pass/fail per case, open trace timelines, and diff two runs side-by-side to highlight regressions
- **CLI** — trigger runs from CI: `rubriclab run --suite=demo`

---

## Quickstart

### Docker (recommended)

```bash
git clone https://github.com/your-org/rubriclab
cd rubriclab
docker compose up
```

- Dashboard: http://localhost:3000
- API: http://localhost:8000
- API health: http://localhost:8000/health

### Local dev

**Prerequisites:** Python 3.12+, [uv](https://docs.astral.sh/uv/), Node 22+, [pnpm](https://pnpm.io/)

```bash
# Install JS dependencies
pnpm install

# Start the API
cd apps/api
uv sync
uv run uvicorn rubriclab.main:app --reload --port 8000

# In another terminal, start the web app
cd apps/web
pnpm dev
```

---

## Architecture

> M2 shipped the SQLite storage layer. Remaining components (AgentRunner, JudgeEngine, dashboard, CLI) ship in M3+.

```
┌─────────────────────────┐    ┌──────────────────────────┐
│  Next.js Dashboard      │    │  CLI: rubriclab run ...  │
│  (suites, runs, traces) │    └────────────┬─────────────┘
└────────────┬────────────┘                 │
             │  REST/JSON                   │
             ▼                              ▼
      ┌─────────────────────────────────────────────┐
      │            FastAPI backend                  │
      │  /suites  /runs  /cases  /traces  /diff     │
      └──┬───────────────┬────────────────┬─────────┘
         │               │                │
         ▼               ▼                ▼
  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
  │ AgentRunner  │ │ JudgeEngine  │ │  SQLite      │
  │ (calls user  │ │ (Anthropic   │ │  (SQLModel)  │
  │  agent +     │ │  rubric      │ │  suites,     │
  │  captures    │ │  scoring)    │ │  cases,      │
  │  trace)      │ │              │ │  runs,       │
  └──────┬───────┘ └──────┬───────┘ │  traces,     │
         │                │         │  scores      │
         ▼                ▼         └──────────────┘
  ┌──────────────────────────────┐
  │  Sample Research Agent       │
  │  (Anthropic + tools)         │
  └──────────────────────────────┘
```

**Core data model:** `Suite 1—* Case`, `Run 1—* CaseResult`, `CaseResult 1—1 Trace`, `CaseResult 1—* RubricScore`. Diff = join two Runs on Case and compute per-dimension deltas.

---

## Demo flow

> This describes the intended experience at M8. Currently the scaffold, health endpoint, web stub, full data model, SQLite storage, and demo suite (seeded at startup) are available.

1. `docker compose up` (or local Python + pnpm dev)
2. Open dashboard → see preloaded **"Research Agent v1"** suite with 8 cases
3. Click **Run** → cases stream in as they complete; pass/fail badges + scores appear live
4. Open a failed case → trace viewer shows the agent making a wrong tool call; judge's justification is shown inline
5. Edit the agent's system prompt in `agents/research/prompt.md`, hit **Run** again
6. Open **Compare runs** → side-by-side diff highlights which 3 cases improved, which 1 regressed, with score deltas per rubric dimension

---

## Roadmap

| Milestone | Description | Status |
|-----------|-------------|--------|
| M1 | Scaffold + README | ✅ Done |
| M2 | SQLite data model (SQLModel) | ✅ Done |
| M3 | Agent runner + trace capture | ⬜ Planned |
| M4 | LLM-as-judge engine | ⬜ Planned |
| M5 | FastAPI routes (/suites, /runs, /cases, /traces, /diff) | ⬜ Planned |
| M6 | Next.js dashboard (suite browser, run trigger, results) | ⬜ Planned |
| M7 | Trace viewer + two-run diff UI | ⬜ Planned |
| M8 | Sample research agent + demo suite | ⬜ Planned |
| M9 | CLI (`rubriclab run --suite=demo`) | ⬜ Planned |

---

## Contributing

Contributions welcome! Please open an issue before submitting a large PR.

1. Fork the repo
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Commit with Conventional Commits: `git commit -m "feat: add thing"`
4. Open a PR

---

## License

MIT © 2024 RubricLab contributors. See [LICENSE](./LICENSE).
