# OpenManus Operational Platform Core

This directory adds a persistent control plane around the existing OpenManus agent engine.

## Architecture

```text
Client
  -> FastAPI API
  -> JWT authentication and project ownership
  -> PostgreSQL / SQLite
  -> Redis queue
  -> OpenManus worker
  -> PolicyToolBroker
  -> Manus engine + tools/MCP/browser
  -> durable task/workflow events
  -> SSE
```

## Capabilities in v0.2

- User registration and JWT authentication.
- Project-scoped tool policies with allow/deny/approval patterns.
- Persistent conversations and task history.
- Persistent memory entries with lightweight keyword retrieval.
- Project knowledge documents with retrieval.
- Durable sequential workflows with persisted step runs.
- Workflow recovery after stale worker heartbeats.
- Cooperative task/workflow cancellation.
- Task and workflow event streams over SSE.
- Audit events for important platform actions.

## Run locally

Copy `.env.platform.example` to `.env`, set a long random `OPENMANUS_JWT_SECRET`, then:

```bash
docker compose -f docker-compose.platform.yml up --build
```

The API is available at `http://localhost:8000`.

Swagger/OpenAPI is available at `/docs`.

## Workflow prompts

Workflow step prompts may use these placeholders:

- `{{input}}` — the workflow run input.
- `{{previous_output}}` — the previous step's output.
- `{{step_index}}` — zero-based step index.

Example:

```json
{
  "name": "Research pipeline",
  "steps": [
    {"name": "Research", "prompt": "Research {{input}} and collect the important facts."},
    {"name": "Synthesize", "prompt": "Using {{previous_output}}, produce a concise synthesis of {{input}}."}
  ]
}
```

## Policy behavior

The project policy is enforced immediately before an OpenManus tool executes. Explicit denies win. Approval-required patterns are denied until an approval mechanism is added in a later platform layer.

The default policy blocks shell, computer-use, sandbox and Docker tool names, while allowing normal planning, Python, web, Crawl4AI and Browser Use tools. Treat this as a development control plane, not a production security boundary until the full sandbox/policy/approval architecture is deployed.

## Persistent memory and knowledge

Memory is durable in PostgreSQL and can be scoped to a project or user. Knowledge documents are project-scoped. Current retrieval is deterministic keyword matching so the feature works without an external embedding service; the storage model is intentionally ready for a future vector/embedding backend.

## Migration note

The platform tables are additive. Existing OpenManus tables are not altered by this change, so a fresh platform database is sufficient for development. A real production migration system (Alembic) should be introduced before schema changes are deployed to live environments.
