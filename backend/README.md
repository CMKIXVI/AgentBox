# AgentBox backend

Python 3.11+ / FastAPI service. The backend is frontend-independent; it exposes OpenAPI-described HTTP endpoints and makes no assumptions about Flutter or any other UI framework.

## Run locally

From this directory:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload
```

The default SQLite database is stored at `backend/data/agentbox.sqlite3`. Override it with `AGENTBOX_DATABASE_PATH`. The API loads the authoritative manifest schema from `../schemas/agent-manifest-v1.schema.json`; override with `AGENTBOX_SCHEMA_PATH` if required.

## API

- `GET /health` — service health.
- `POST /v1/agents/validate` — validate a manifest without storing it.
- `POST /v1/agents` — validate and create an immutable agent version.
- `GET /v1/agents/{agent_id}/versions` — list versions.
- `GET /v1/agents/{agent_id}/versions/{version}` — retrieve a version.
- `POST /v1/agents/{agent_id}/versions/{version}/clone` — create a derived version with parent lineage.

Interactive API documentation is available at `/docs`; the OpenAPI document is at `/openapi.json`.

## Current boundary

This is the first registry vertical slice, not an agent execution runtime. It does not resolve secrets, invoke models, execute tools, run workflows, or grant permissions. Manifest validation uses the repository JSON Schema; every imported manifest remains untrusted input. SQLite is suitable for local development and early tests, not yet a multi-instance production deployment.
