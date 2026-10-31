# Empório da Música — Melody, the customer service agent

AI customer-service agent for Empório da Música, a fictional musical instrument store in Campo
Grande/MS (Artefact AI Engineer challenge). Work in progress — see the
[backlog](docs/planning/backlog.md) and the [decision log](docs/decision-log.md).

## Repository layout

| Path | What |
|---|---|
| `backend/` | Python API (FastAPI; LangGraph agent and MCP server to come) |
| `frontend/` | Next.js chat UI |
| `challenge/` | Original brief and store data (read-only inputs) |
| `specs/` | Spec Kit artifacts per epic |
| `docs/` | Decision log, planning, contracts |

## Run locally

Requirements: Docker, [uv](https://docs.astral.sh/uv/), Node 24 with pnpm (`corepack enable pnpm`).

```bash
# Database (Postgres 16 + pgvector on localhost:5433)
docker compose up -d --wait

# Backend
cd backend
cp .env.example .env
uv sync
uv run pytest
uv run uvicorn app.main:app --reload   # http://localhost:8000/api/health

# Frontend (in another terminal)
cd frontend
pnpm install
pnpm dev                               # http://localhost:3000
```

No API keys are needed to run the tests: providers default to deterministic fakes.
