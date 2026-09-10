# OpenManus Operational Platform

This layer adds a persistent control plane around the existing OpenManus agent engine without replacing the engine.

## v0.3 capabilities

- JWT authentication with Argon2 password hashing.
- Persistent projects, conversations, tasks and audit events.
- Redis-backed workers with database recovery.
- Project-scoped tool policies.
- Approval requests for high-risk tool execution.
- Host execution boundary that blocks Bash, Docker and computer-use tools unless separately isolated.
- Durable user/project memory and project knowledge records.
- Durable sequential workflows with persisted step runs and stale-run recovery.
- Durable artifact storage using a local persistent volume or S3-compatible object storage.
- Project quotas and token/cost accounting with configurable rates.
- Vanilla HTML web console at `/`.
- Alembic schema migrations.

## Run

For local Docker development:

```bash
docker compose -f docker-compose.platform.yml up --build
```

The compose stack runs PostgreSQL, Redis, migrations, the API and a dedicated OpenManus worker.

The web console is available at `http://localhost:8000/` and API documentation at `http://localhost:8000/docs`.

For non-Docker development, set the environment variables from `.env.platform.example`, run `alembic upgrade head`, then start the API and worker separately.

## Approval behavior

A project policy can mark a tool pattern as approval-required. The worker pauses the task with status `awaiting_approval` and creates a durable approval request. Approving the request requeues the task; denying it permanently fails that task.

Approval currently re-queues the task from its persisted prompt rather than checkpointing the exact in-memory agent state. Do not use approval-required patterns for non-idempotent side effects until checkpointed tool execution is added.

## Execution boundary

The platform blocks direct Bash, Docker and computer-use tools. Sandbox-pattern tools require `OPENMANUS_SANDBOX_ENABLED=true` and should be backed by an actual isolated sandbox service before public deployment. The default project policy is deliberately conservative.

## Storage

Artifacts are scoped to a project and owner. With `OPENMANUS_S3_BUCKET` configured, uploads go to the configured S3-compatible object store and API responses expose short-lived presigned download URLs. Without S3 configuration, files are stored under `OPENMANUS_ARTIFACT_ROOT` on the persistent application volume.

## Usage and quotas

Each project has monthly token/task and concurrent-task limits. Usage is estimated deterministically from stored text at roughly four characters per token and priced with `OPENMANUS_USAGE_INPUT_RATE` and `OPENMANUS_USAGE_OUTPUT_RATE`. These are platform accounting estimates and should be replaced with provider-reported usage for billing-grade accounting.

## Database migrations

Production deployments should run:

```bash
alembic upgrade head
```

The API can still auto-create tables for isolated local development with `OPENMANUS_AUTO_CREATE_DB=true`. Production should keep this disabled.

## Important deployment boundary

This is a development-oriented operational platform, not a finished public SaaS. Before exposing untrusted users, run the full integration test suite in CI, use a real secrets manager, enable a real isolated sandbox backend, add rate limits/tenant roles, and verify provider-reported billing usage.
