# RubricLab

> **Evaluation harness for AI agents.** Define structured test suites with rubrics, run your agent against them, get LLM-as-judge scores, inspect full execution traces, and diff runs over time to catch regressions.

![Status](https://img.shields.io/badge/status-alpha-orange)
![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.12-blue)
![Next.js](https://img.shields.io/badge/next.js-15-black)

![Dashboard screenshot](docs/screenshot.png)

---

## What is RubricLab?

Building an agent is easy. Knowing whether yesterday's prompt tweak made it *better or worse* is hard.

Most teams ship agents with vibes-based testing — a few manual prompts, no structured rubric, no regression catching. RubricLab is the missing dev-loop tool: write test cases once, score every change automatically, and see exactly where behavior drifted.

### What works today (M8)

**M1 — scaffold**
- Monorepo: `apps/api` (FastAPI), `apps/web` (Next.js 15), `packages/shared` TypeScript types
- `GET /` and `GET /health` live; dev tooling (uv + ruff, pnpm + prettier + eslint)

**M2 — data model + storage**
- SQLModel entities: `Suite`, `Case`, `Run`, `CaseResult`, `Trace`, `RubricScore`
- SQLite bootstrap on startup; demo suite "Research Agent v1" (8 cases) seeded idempotently

**M3 — agent runner + trace capture**
- `AgentRunner` protocol (`apps/api/src/rubriclab/runner.py`); `ResearchAgent` with `web_search` + `calculator` tools

**M4 — LLM-as-judge engine**
- Anthropic-powered rubric scoring with per-dimension scores and written justifications

**M5 — FastAPI routes**
- `/suites`, `/runs`, `/cases`, `/traces`, `/diff` REST endpoints

**M6 — Next.js dashboard**
- Suite browser, run trigger, pass/fail results with score breakdown

**M7 — Trace viewer + diff UI**
- Timeline of tool calls/messages; side-by-side two-run diff with score deltas

**M8 — demo packaging**
- `docker compose up --build` runs everything end-to-end
- `record_demo.sh` triggers two runs with a system-prompt tweak between them, captures screenshots via Playwright (falls back to manual URLs), and saves them to `docs/`
- `.env.example` documents the only required secret (`ANTHROPIC_API_KEY`)

---

## Quickstart

### Docker (recommended)

```bash
git clone https://github.com/your-org/rubriclab
cd rubriclab
cp .env.example .env          # add your ANTHROPIC_API_KEY
docker compose up --build
```

To run the full demo and compare two runs:

```bash
./record_demo.sh
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

> M8 shipped end-to-end: all components from AgentRunner through dashboard and diff UI are live.

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

![Demo](docs/demo.gif)

> Fully runnable end-to-end as of M8. Every step below works with `docker compose up --build` or local dev.

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
| M3 | Agent runner + trace capture | ✅ Done |
| M4 | LLM-as-judge engine | ✅ Done |
| M5 | FastAPI routes (/suites, /runs, /cases, /traces, /diff) | ✅ Done |
| M6 | Next.js dashboard (suite browser, run trigger, results) | ✅ Done |
| M7 | Trace viewer + two-run diff UI | ✅ Done |
| M8 | Demo packaging (docker compose, record_demo.sh) | ✅ Done |
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
