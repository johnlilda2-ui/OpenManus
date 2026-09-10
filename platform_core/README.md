# OpenManus Operational Platform

This layer adds a persistent, governed control plane around the existing OpenManus agent engine without replacing the engine.

## Hardened platform capabilities

- JWT authentication with Argon2 password hashing.
- Tenant membership with viewer/member/admin/owner roles.
- Project-scoped tool policy with explicit deny, allow, and approval rules.
- Durable approval requests and approve/deny endpoints.
- Direct host Bash, Docker, and computer-use execution blocked by the platform boundary.
- Production sandbox path using Daytona; the official Python SDK is pinned to `daytona==0.210.0` in this branch. Daytona documents its sandboxes as isolated execution environments. citeturn633941search3turn633941search1
- Persistent projects, conversations, tasks, workflow runs and audit events.
- Persistent user/project memory and project knowledge retrieval.
- Durable sequential workflows with heartbeat recovery.
- Durable artifacts on a persistent local volume or S3-compatible object storage.
- Redis-backed API rate limiting with a stricter authentication limit.
- Monthly task/token quotas and concurrent-task limits.
- Provider-reported token usage captured from OpenManus LLM responses where the provider returns usage data; estimated accounting remains the fallback for paths without provider counters.
- Alembic migrations with PostgreSQL CI coverage.
- Web operational console at `/`.

## Development

```bash
cp .env.platform.example .env
pip install -r requirements.txt
alembic upgrade head
uvicorn platform_core.api:app --reload
```

Run the worker separately:

```bash
python -m platform_core.worker
```

Or use the development compose stack:

```bash
docker compose -f docker-compose.platform.yml up --build
```

## Production configuration

Production must use:

- `OPENMANUS_ENV=production`
- `OPENMANUS_AUTO_CREATE_DB=false`
- a mounted JWT secret file
- `OPENMANUS_SANDBOX_ENABLED=true`
- `OPENMANUS_SANDBOX_BACKEND=daytona`
- Redis rate limiting with `OPENMANUS_RATE_LIMIT_FAIL_OPEN=false`
- a persistent artifact store or S3-compatible object storage
- a real PostgreSQL database
- provider credentials supplied through mounted secrets rather than committed configuration values

The production compose profile is provided as `docker-compose.production.yml`. It runs Alembic migrations before the API/worker and mounts separate JWT, LLM, and Daytona secrets.

## Secret-backed provider configuration

Use `secret://<name>` in `config/config.toml` for provider credentials, for example:

```toml
[llm]
api_key = "secret://openmanus_llm_api_key"

[daytona]
daytona_api_key = "secret://openmanus_daytona_api_key"
```

The runtime resolves these values from mounted secret files or `OPENMANUS_SECRET_*` environment variables without writing the secret value to the platform database.

## Approval behavior

A project policy can mark a tool pattern as approval-required. The worker pauses the task with status `awaiting_approval` and creates a durable approval request. Approving the request requeues the task; denying it permanently fails the task.

Approval currently re-queues the task from its persisted prompt rather than checkpointing the exact in-memory agent state. Do not use approval-required patterns for non-idempotent side effects until checkpointed tool execution is added.

## Database migrations

Run:

```bash
alembic upgrade head
```

Production should never depend on automatic `Base.metadata.create_all`; that mode is for isolated local development only.

## Usage accounting

The OpenManus `ask_tool` path exposes provider-returned `prompt_tokens` and `completion_tokens`, which the worker records as `usage_source=provider`. This repository still uses a deterministic text estimate as a fallback for execution paths where provider usage is unavailable.

## Security boundary

This is a production-hardening slice, not a claim that every deployment is automatically secure. Public deployment still requires correct secret provisioning, isolated Daytona configuration, network controls, rate-limit tuning, dependency updates, observability, backup/restore testing, and an environment-specific security review.