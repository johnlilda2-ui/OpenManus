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
Treat that directory as the project root. Do not modify files outside
unless explicitly required. Preserve existing work when present.
The goal is a complete, runnable full-stack application, not a mockup.
Requirements from the user:
{requirements}
""".strip()
    phase_data = [
        ("Requirements and architecture", "planner", f"""{shared}
Analyze the requirements and inspect any existing project files. Create {workspace}/APP_PLAN.md containing product requirements, acceptance criteria, architecture, data model, API contract, UI pages/components, test strategy, and deployment requirements. Do not implement yet.""", 1, False),
        ("Backend implementation", "builder", f"""{shared}
Read APP_PLAN.md. Implement the backend first. Prefer FastAPI + Pydantic when appropriate. Create working API routes, validation, persistence, authentication when required, and backend tests. Keep configuration in environment variables and add a safe .env.example. Run tests and fix failures.""", 2, False),
        ("Frontend implementation", "designer", f"""{shared}
Read APP_PLAN.md and the backend API. Implement a production-quality frontend. Prefer React + Vite + Tailwind when appropriate. Build responsive UX, loading/empty/error states, accessible controls, clear navigation, polished hierarchy, and real API integration. Run the frontend build and fix errors.""", 2, False),
        ("Integration and preview configuration", "builder", f"""{shared}
Integrate frontend and backend end-to-end. Add docker-compose.yml when useful, startup scripts, environment templates, database initialization/migrations, and a README with exact run instructions.
Create {workspace}/APP_PREVIEW.json with the safest local preview command, non-privileged port, health_path, and cwd. The command will run inside the isolated sandbox only.""", 2, False),
        ("Run and preview", "tester", f"""{shared}
Read APP_PREVIEW.json and launch the application inside the isolated sandbox using sandbox_shell in a persistent named session. Do not run it on the host. Curl the configured health_path, fix launch/runtime errors, then call sandbox_preview with the configured port to obtain the browser-accessible preview URL. Write {workspace}/PREVIEW_REPORT.md with command, port, health result, preview URL, startup logs, and stop-session instructions. Leave the preview running for QA; if sandbox tools are unavailable, document that instead of host execution.""", 2, False),
        ("Automated test and repair", "tester", f"""{shared}
Read PREVIEW_REPORT.md. Run backend/frontend tests, linters/type checks when configured, and production builds. Diagnose failures, fix them, and rerun checks until they pass or an external dependency/credential is the only blocker. Record results in {workspace}/QA_REPORT.md.""", 3, False),
        ("Browser verification", "reviewer", f"""{shared}
Perform real browser QA against the running preview. Read PREVIEW_REPORT.md and use its preview URL; do not invent another URL. Use sandbox_browser to inspect rendering and exercise the most important user flow. Check navigation, forms, validation, runtime issues, states, responsiveness, visual hierarchy, and accessibility basics. Do not fix here. Write {workspace}/QA_FAILURES.md and end with exactly QA_STATUS: PASS or QA_STATUS: FAIL. If browser tooling is unavailable, report QA_STATUS: FAIL.""", 2, True),
        ("Autonomous repair", "fixer", f"""{shared}
Read QA_FAILURES.md and PREVIEW_REPORT.md. If QA_STATUS: PASS, make no functional changes. If QA_STATUS: FAIL, fix reproducible browser issues in the isolated workspace, restart preview when required, rerun focused checks, and write {workspace}/REPAIR_REPORT.md. End with REPAIR_STATUS: FIXED or REPAIR_STATUS: BLOCKED.""", 2, False),
        ("Browser re-verification", "reviewer", f"""{shared}
Re-run browser QA after repair using the same preview when possible. Exercise the same failures and confirm fixes. Update {workspace}/QA_REPORT.md. End with QA_STATUS: PASS if verified; otherwise QA_STATUS: FAIL. Never claim checks you could not perform.""", 2, True),
        ("Final security and release review", "reviewer", f"""{shared}
Perform a final release review for secrets, unsafe debug settings, missing environment documentation, authorization bypasses, insecure input handling, dependency/config mistakes, and broken setup instructions. Read the QA/release reports. Fix local issues. Produce {workspace}/RELEASE_CHECKLIST.md and {workspace}/FINAL_REPORT.md stating verified checks, unverified checks, blockers, and preview URL.""", 1, False),
    ]
    return [{"name": name, "prompt": prompt, "model_profile": role, "role": role, "max_attempts": attempts, "browser_required": browser_required} for name, role, prompt, attempts, browser_required in phase_data]
