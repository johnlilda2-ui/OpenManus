from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BuilderStep:
    name: str
    role: str
    prompt: str
    max_attempts: int = 1
    browser_required: bool = False


def project_workspace(project_id: str) -> str:
    return f"workspace/projects/{project_id}"


def build_app_builder_steps(project_id: str, requirements: str) -> list[dict]:
    workspace = project_workspace(project_id)
    shared = f"""
You are working on a dedicated software project in {workspace}.
Treat that directory as the project root. Do not modify files outside it unless
explicitly required by the task. Preserve existing work when present.
The goal is a complete, runnable full-stack application, not a mockup.
The generated application should include a polished responsive UI, a working
backend, validation, clear environment variables, tests, and a README.
Requirements from the user:
{requirements}
""".strip()
    steps = []
    steps.append(BuilderStep(name="Requirements and architecture", role="planner", prompt=f"""{shared}

Analyze the requirements and inspect any existing project files. Create {workspace}/APP_PLAN.md containing:
- product requirements and acceptance criteria
- frontend/backend architecture
- data model and API contract
- UI pages/components and responsive states
- test strategy
- local development and deployment requirements
Do not implement the application yet."""))
    steps.append(BuilderStep(name="Backend implementation", role="builder", prompt=f"""{shared}

Read APP_PLAN.md. Implement the backend first. Prefer FastAPI + Pydantic when a
Python backend is appropriate. Create working API routes, validation, error
handling, persistence, authentication when required by the requirements, and
backend tests. Keep configuration in environment variables and add a safe
.env.example. Run the backend tests and fix failures before finishing.""", max_attempts=2))
    steps.append(BuilderStep(name="Frontend implementation", role="designer", prompt=f"""{shared}

Read APP_PLAN.md and the backend API. Implement a production-quality frontend.
Prefer React + Vite with Tailwind CSS when appropriate. Build the complete user
experience, not placeholder cards: responsive layout, loading/empty/error
states, accessible controls, consistent typography and spacing, clear
navigation, useful micro-interactions, and polished visual hierarchy. Connect
real API data instead of mock-only data. Run the frontend build and fix errors.""", max_attempts=2))
    steps.append(BuilderStep(name="Integration and preview configuration", role="builder", prompt=f"""{shared}

Integrate frontend and backend end-to-end. Remove fake/mock data paths that are
not required for the finished application. Add docker-compose.yml when useful,
startup scripts, environment templates, database initialization/migrations,
and a README with exact run instructions. Verify that the application can be
started from a clean checkout.

Also create {workspace}/APP_PREVIEW.json describing the safest local preview:
{{
  "command": "the exact command to start the preview server",
  "port": 3000,
  "health_path": "/",
  "cwd": "."
}}
Use a non-privileged port. The command will run inside the isolated project
sandbox only. Keep the preview server suitable for browser verification.""", max_attempts=2))
    steps.append(BuilderStep(name="Run and preview", role="tester", prompt=f"""{shared}

Read APP_PREVIEW.json and launch the application inside the isolated sandbox.
Use sandbox_shell to run the exact preview command in a persistent named session.
Do not run the application on the host machine.

Verify the preview from inside the sandbox with curl against the configured
health_path. Inspect the startup output and fix launch/runtime errors. Then use
the sandbox_preview tool with the configured port to obtain the browser-accessible
preview URL. Write {workspace}/PREVIEW_REPORT.md containing:
- start command
- port and health path
- local health result
- preview URL
- relevant startup logs
- exact command/session needed to stop the preview

Leave the preview process running for the following QA phases unless it cannot
be started safely. If isolated sandbox tools are unavailable, document that
preview execution could not be performed rather than attempting host execution.""", max_attempts=2))
    steps.append(BuilderStep(name="Automated test and repair", role="tester", prompt=f"""{shared}

Act as a release engineer. Read PREVIEW_REPORT.md if present and run the backend
tests, frontend tests if present, linters/type checks where configured, and
production builds. Diagnose failures instead of merely reporting them. Fix the
implementation and rerun the failed checks. Continue until the available
automated checks pass or a real external credential/dependency is clearly the
only blocker. Record the final checks and any blockers in {workspace}/QA_REPORT.md.""", max_attempts=3))
    steps.append(BuilderStep(name="Browser verification", role="reviewer", browser_required=True, prompt=f"""{shared}

Perform real browser-level QA against the running preview. Read
PREVIEW_REPORT.md and use its preview URL; do not invent another URL. Use
sandbox_browser to navigate to the application and inspect the actual rendered
UI. Exercise the most important user flow from the requirements. Check:
- initial page/rendering
- navigation and links
- forms and validation states
- obvious console/runtime failures when observable
- loading, empty and error states
- responsive behavior where the browser tooling allows it
- visual hierarchy, spacing and accessibility basics

Do NOT silently fix issues in this phase. Record reproducible failures and their
likely causes in {workspace}/QA_FAILURES.md. End your response with exactly one
of:
QA_STATUS: PASS
QA_STATUS: FAIL

For PASS, explain what was actually verified. For FAIL, provide concise,
actionable failure details for the repair phase. If browser tooling is not
available, end with QA_STATUS: FAIL and clearly state that verification was not
performed.""", max_attempts=2))
    steps.append(BuilderStep(name="Autonomous repair", role="fixer", prompt=f"""{shared}

Read QA_FAILURES.md and PREVIEW_REPORT.md. If the previous browser verification
reported QA_STATUS: PASS, do not make functional changes; simply record that no
repair was necessary.

If QA_STATUS: FAIL, fix every reproducible browser issue you can. Use the
sandbox shell/files tools only inside the isolated workspace. Restart the preview
process when required, rerun focused automated checks, and update
{workspace}/REPAIR_REPORT.md with each repair and its verification result.
Finish by stating either REPAIR_STATUS: FIXED or REPAIR_STATUS: BLOCKED.""", max_attempts=2))
    steps.append(BuilderStep(name="Browser re-verification", role="reviewer", browser_required=True, prompt=f"""{shared}

Re-run browser QA after the repair phase. Read PREVIEW_REPORT.md and
REPAIR_REPORT.md and use the same running preview when possible. Exercise the
same failures again and confirm the repaired behavior.

If everything passes, update {workspace}/QA_REPORT.md with the final browser
verification and end with:
QA_STATUS: PASS

If anything still fails, update QA_FAILURES.md with the remaining reproducible
problems and end with:
QA_STATUS: FAIL

Do not claim success for checks you could not actually perform. If browser
verification is unavailable, report QA_STATUS: FAIL rather than inventing a pass.""", max_attempts=2))
    steps.append(BuilderStep(name="Final security and release review", role="reviewer", prompt=f"""{shared}

Perform a final release review. Check for hard-coded credentials/secrets,
unsafe debug settings, missing environment documentation, obvious authorization
bypasses, insecure input handling, dependency/configuration mistakes, and broken
setup instructions. Read PREVIEW_REPORT.md, QA_REPORT.md and REPAIR_REPORT.md
when present. Fix issues that can be fixed locally. Produce:
- {workspace}/RELEASE_CHECKLIST.md
- {workspace}/FINAL_REPORT.md
The final report must state what was verified, what was not verified, any
remaining blockers, and the preview URL when one was successfully created."""))
    return [{"name": s.name, "prompt": s.prompt, "model_profile": s.role, "role": s.role, "max_attempts": s.max_attempts, "browser_required": s.browser_required} for s in steps]
