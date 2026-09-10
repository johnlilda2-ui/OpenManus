# OpenManus Operational Platform Core

This directory adds a production-oriented control plane around the existing OpenManus engine without replacing it.

## Included in v0.1.0

- JWT authentication with Argon2 password hashing
- PostgreSQL-ready persistence (SQLite is the local fallback)
- Users, projects, conversations, messages, tasks, task events and audit events
- Redis-backed background task queue
- Dedicated worker that executes the existing `Manus` agent
- Server-Sent Events for live task state updates
- Cooperative task cancellation
- Per-user ownership checks for platform resources
- Docker Compose development stack with PostgreSQL, Redis, API and worker

## Local development

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Copy `.env.platform.example` values into your environment. For production, set a strong `OPENMANUS_JWT_SECRET`.

3. Make sure the existing OpenManus LLM configuration is available at `config/config.toml`.

4. Start Redis locally, then run the API:

```bash
uvicorn platform_core.api:app --reload
```

5. In a second terminal, start the worker:

```bash
python -m platform_core.worker
```

API documentation is available at `http://127.0.0.1:8000/docs`.

## Docker Compose

```bash
docker compose -f docker-compose.platform.yml up --build
```

The compose file supplies PostgreSQL and Redis. OpenManus still reads its normal model configuration from `config/config.toml`.

## API flow

```text
register/login
    -> create project
    -> create conversation
    -> create task
    -> Redis queue
    -> OpenManus worker
    -> task events
    -> SSE stream
    -> persistent assistant message + audit event
```

## Important security boundary

The existing OpenManus engine contains powerful local execution tools such as Bash and Python. The platform core currently protects resources at the user/tenant boundary, but a production deployment should add a centralized tool policy and isolated execution broker before exposing arbitrary code execution to untrusted users.

## Next platform layers

1. Database migrations (Alembic)
2. Central policy/tool broker with approval gates
3. Persistent long-term memory and project knowledge/RAG
4. Durable resumable workflows and multi-agent orchestration
5. Artifact/object storage and download permissions
6. Usage, quotas, cost controls and billing hooks
7. Web application and WebSocket/SSE task UI
8. Metrics, tracing and production alerting
