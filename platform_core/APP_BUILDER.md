# OpenManus App Builder

The App Builder turns a project requirement into a durable multi-phase workflow instead of a single prompt. It is designed for full-stack application generation with verification and repair.

## Pipeline

1. Requirements and architecture (`planner`)
2. Backend implementation (`builder`)
3. Frontend implementation (`designer`)
4. Integration and developer experience (`builder`)
5. Automated test and repair (`tester`)
6. Browser and visual QA (`reviewer`)
7. Final security and release review (`reviewer`)
8. Application ZIP artifact delivery

Each phase is persisted as a `WorkflowStepRun`. Failed phases can retry according to their `max_attempts` value. Builder runs use `builder_queued` / `builder_running` statuses so they have their own queue and recovery semantics without changing the existing general worker.

## Model routing

The workflow stores a logical role and an optional model profile for every phase. The router resolves the requested profile, then falls back to the configured `default` profile when that profile is unavailable.

Supported logical roles are:

- `planner`
- `builder`
- `designer`
- `tester`
- `fixer`
- `reviewer`

A deployment can override a role with environment variables such as `OPENMANUS_MODEL_PLANNER=planner` or `OPENMANUS_MODEL_DESIGNER=designer`. Provider credentials remain external secrets; they are never embedded into the workflow definition.

The underlying OpenManus LLM layer remains provider-neutral. A profile is simply a key in the existing `[llm.<profile>]` configuration, so an OpenAI-compatible endpoint, Gemini-compatible endpoint, OpenRouter, DeepSeek, Groq, or another supported endpoint can be selected without changing the builder workflow itself.

## Creating a builder run

The current platform-safe entrypoint is:

```bash
python -m platform_core.app_builder_cli \
  --project-id <PROJECT_ID> \
  --user-id <USER_ID> \
  --requirements "Build a responsive full-stack SaaS dashboard with authentication, a PostgreSQL-backed API, and a polished React UI."
```

Start the dedicated builder worker with:

```bash
python -m platform_core.app_builder_worker
```

The normal platform worker does not consume the App Builder queue.

## Workspace

Development runs use:

`workspace/projects/<project_id>`

Production sandbox runs use the corresponding isolated Daytona workspace. The final builder phase creates `application.zip` and stores it through the platform artifact service with SHA-256 integrity metadata.

## Browser QA

The browser QA phase is explicitly marked `browser_required`. In a sandboxed production run, the agent can use the existing sandbox browser capabilities to inspect the generated application. When browser tooling is unavailable, the phase is instructed to record the limitation rather than claim a successful visual test.

## Important boundary

The App Builder is an orchestration layer, not a guarantee that every generated application is production-safe. Generated code is still subject to the platform's policy, sandbox, approval, quota, and release-review controls. A real provider credential and an enabled isolated sandbox are required for production execution.
