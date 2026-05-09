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

### What works today (M1–M4)

**M1 — Scaffold**

- Monorepo scaffold: `apps/api` (FastAPI), `apps/web` (Next.js 15), `packages/shared` TypeScript types
- FastAPI skeleton boots at `localhost:8000`; `GET /` and `GET /health` are live
- Next.js 15 app scaffold at `localhost:3000`
- Shared TypeScript domain types: `Suite`, `Case`, `Run`, `CaseResult`, `Trace`, `TraceEvent`, `RubricDimension`, `RubricScore` (see `packages/shared/src/index.ts`)
- Dev tooling configured: uv + ruff for Python, pnpm + prettier + eslint for JS/TS
- Docker Compose stub wires both services with a named SQLite volume
- MIT license, `.gitignore`, `.prettierrc`

**M2 — SQLite data model**

- SQLModel ORM tables: `Suite`, `Case`, `Run`, `CaseResult`, `Trace`, `RubricScore`
- `repository.py` — typed CRUD helpers for all entities
- `seed.py` — pre-loads a demo suite with sample cases on first boot
- Zero external database dependencies; single SQLite file, fully portable

**M3 — Agent runner + trace capture**

- `AgentRunner` Protocol (`runner.py`) — pluggable interface: `run(input, context) -> TraceResult`
- `TraceResult` dataclass — `final_output`, `events`, `latency_ms`, `input_tokens`, `output_tokens`; `RunResult` is a backward-compatible alias
- `run_case()` orchestrator — executes one test case, writes `CaseResult` and `Trace` to SQLite
- `ResearchAgent` (`agents/research.py`) — sample agent backed by Anthropic Claude Haiku with two tools:
  - `web_search` — canned keyword-match stub returning deterministic results (no live network call required)
  - `calculator` — AST-based safe arithmetic evaluator; rejects anything that is not a numeric expression
- Full trace capture per agent loop iteration: `model_call` (with stop reason and per-call token counts), `tool_call`, `tool_result`, and `final_output` events, each timestamped in UTC ISO-8601
- Aggregate latency (wall-clock ms) and token totals accumulated across all agentic loop turns
- System prompt loaded from `agents/research/prompt.md` at repo root — edit it to change agent behavior without touching source code; inline fallback if the file is absent
- Optional `api_key` constructor argument; unit tests mock the Anthropic class via `unittest.mock.patch` — no live API key required to run the test suite

**M4 — LLM-as-judge engine**

- `JudgeEngine` (`judge.py`) — scores a `TraceResult` against a list of rubric dimensions using Anthropic tool-use (`submit_scores`), forcing structured JSON output and eliminating free-text parsing
- `DimensionScore` dataclass — `dimension_id`, `dimension_name`, `score` (0.0–1.0, clamped), `justification` (one sentence from the judge)
- `JudgeResult` dataclass — `scores: list[DimensionScore]`, `weighted_score` (normalised by dimension weights), `passed` bool
- Configurable `pass_threshold` (default 0.7); weights need not sum to 1.0 — the engine normalises them automatically
- Empty-rubric guard: if a case has no dimensions, returns `passed=False` immediately without an API call
- Graceful fallback: if the Claude call fails, all scores default to 0.0 and the case is marked failed
- `run_case()` extended with optional `judge` parameter — when provided, persists `RubricScore` rows (with `dimension_name`) to SQLite and sets `CaseResult.passed`
- Rubric YAML DSL (`rubrics/research-v1.yaml`, `rubrics/research_agent.yaml`): each dimension defines `id`, `name`, `description`, and `weight`; a suite-level `pass_threshold` key overrides the engine default — schema reference for the M5 CLI loader

### Planned

- **FastAPI routes** — `/suites`, `/runs`, `/cases`, `/traces`, `/diff` REST endpoints
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

> Architecture as of M4. `AgentRunner`, `ResearchAgent`, SQLite persistence, and `JudgeEngine` are live. REST routes and dashboard ship in M5–M6.

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

> This describes the intended experience at M8. The data model, agent runner, trace capture, and judge engine are live (M1–M4); the REST API, dashboard, and CLI ship in M5–M9.

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
| M3 | Agent runner, trace capture + sample research agent | ✅ Done |
| M4 | LLM-as-judge engine | ✅ Done |
| M5 | FastAPI routes (/suites, /runs, /cases, /traces, /diff) | ⬜ Planned |
| M6 | Next.js dashboard (suite browser, run trigger, results) | ⬜ Planned |
| M7 | Trace viewer + two-run diff UI | ⬜ Planned |
| M8 | End-to-end demo + polish | ⬜ Planned |
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
