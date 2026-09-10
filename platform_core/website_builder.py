from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WebsiteStep:
    name: str
    role: str
    prompt: str
    max_attempts: int = 1
    browser_required: bool = False


def build_website_builder_steps(project_id: str, requirements: str) -> list[dict]:
    workspace = f"workspace/projects/{project_id}"
    shared = f"""
You are building a real production-quality website in {workspace}.
Treat that directory as the website project root and do not modify files outside it.
Preserve existing work when present and improve it rather than replacing good work.
The finished result must be a runnable website, not a static mockup or design concept.
Prioritize strong visual hierarchy, responsive behavior, accessibility, performance,
SEO, real content structure, maintainable components, and clear setup instructions.
User requirements:
{requirements}
""".strip()

    steps = [
        WebsiteStep(
            name="Website strategy and information architecture",
            role="planner",
            prompt=f"""{shared}

Analyze the requirements and inspect any existing project files. Create {workspace}/WEBSITE_PLAN.md containing:
- target audience and primary conversion goal
- sitemap/page list and navigation hierarchy
- content sections and calls to action for every page
- visual direction, typography, spacing and component system
- responsive behavior for mobile/tablet/desktop
- accessibility requirements
- SEO strategy including titles, descriptions, canonical URLs, robots, sitemap, Open Graph/Twitter metadata and structured data where appropriate
- performance strategy and image/media guidance
- browser acceptance criteria for the most important journeys
Do not implement the website yet.""",
        ),
        WebsiteStep(
            name="Content and page system",
            role="builder",
            prompt=f"""{shared}

Read WEBSITE_PLAN.md. Establish the site's content model and page/component structure.
Create the routes/pages required by the plan, shared navigation/footer, reusable sections,
and clear content placeholders only where user-supplied information is genuinely missing.
Do not use lorem ipsum. Write useful realistic copy based on the requirements and clearly
mark any assumptions. Keep content easy to edit and prepare the site for real API/content
integration when the requirements call for it.""",
            max_attempts=2,
        ),
        WebsiteStep(
            name="Visual frontend implementation",
            role="designer",
            prompt=f"""{shared}

Read WEBSITE_PLAN.md and the current page/component system. Build the polished frontend.
Prefer React + Vite + Tailwind CSS when appropriate. Use a coherent design system instead
of one-off styling. Implement responsive layouts, strong typography, useful micro-interactions,
accessible controls, mobile navigation, loading/empty/error states where applicable, and
real content rather than generic placeholder cards. Use image/media assets deliberately,
with descriptive alt text and performance-conscious sizing. Ensure every navigation link,
CTA, form and page is connected.""",
            max_attempts=2,
        ),
        WebsiteStep(
            name="SEO, accessibility and performance hardening",
            role="builder",
            prompt=f"""{shared}

Audit the website against WEBSITE_PLAN.md. Implement page-specific SEO titles/descriptions,
canonical URLs, robots.txt, sitemap.xml, Open Graph/Twitter metadata, favicon/app metadata,
and relevant schema.org structured data. Add semantic landmarks, heading hierarchy, labels,
keyboard focus states, accessible names, contrast-safe UI, reduced-motion handling where
appropriate, and meaningful alt text. Remove duplicate metadata and obvious performance
problems. Run the available build/lint/type checks and fix failures.""",
            max_attempts=2,
        ),
        WebsiteStep(
            name="Integration and preview configuration",
            role="builder",
            prompt=f"""{shared}

Integrate all pages and interactions end-to-end. Remove fake/mock paths that are not needed
for the finished website. Add a clean README, .env.example when configuration is needed,
and exact local run instructions. Create {workspace}/APP_PREVIEW.json describing the safest
preview command, non-privileged port, health_path and cwd. Keep the preview suitable for
sandbox browser verification.""",
            max_attempts=2,
        ),
        WebsiteStep(
            name="Run and preview",
            role="tester",
            prompt=f"""{shared}

Read APP_PREVIEW.json and launch the website inside the isolated sandbox using sandbox_shell
in a persistent named session. Never run it on the host. Curl the configured health_path and
inspect startup output. Fix launch/runtime errors. Then use sandbox_preview with the configured
port to obtain the browser-accessible preview URL. Write {workspace}/PREVIEW_REPORT.md with:
- start command
- port and health path
- local health result
- preview URL
- relevant startup logs
- exact command/session needed to stop the preview
Leave the preview running for the QA phases whenever safely possible. If sandbox tooling is
unavailable, document that preview execution could not be performed.""",
            max_attempts=2,
        ),
        WebsiteStep(
            name="Automated website test and repair",
            role="tester",
            prompt=f"""{shared}

Read PREVIEW_REPORT.md. Run available frontend tests, build, lint, type checks and any
configured link/accessibility checks. Verify every planned route can build successfully and
that there are no obvious broken references, missing assets or console/build errors. Diagnose
failures, fix them and rerun the failed checks. Record the final state in {workspace}/QA_REPORT.md.""",
            max_attempts=3,
        ),
        WebsiteStep(
            name="Browser visual and UX verification",
            role="reviewer",
            browser_required=True,
            prompt=f"""{shared}

Perform real browser QA against the running preview URL from PREVIEW_REPORT.md. Do not invent
a URL. Use sandbox_browser to inspect representative pages and exercise the primary conversion
journey. Check:
- page rendering and typography
- navigation and mobile navigation
- links and CTA destinations
- forms, validation and error states
- responsive behavior across available viewport controls
- image loading and obvious visual defects
- spacing, hierarchy, consistency and perceived polish
- keyboard/focus accessibility basics when observable
- obvious browser/runtime errors
Do not silently fix issues in this phase. Record reproducible problems in
{workspace}/QA_FAILURES.md and finish with exactly QA_STATUS: PASS or QA_STATUS: FAIL.
If browser tooling is unavailable, report QA_STATUS: FAIL.""",
            max_attempts=2,
        ),
        WebsiteStep(
            name="Autonomous website repair",
            role="fixer",
            prompt=f"""{shared}

Read QA_FAILURES.md and PREVIEW_REPORT.md. If QA_STATUS: PASS, do not make functional changes;
record that no repair was necessary in {workspace}/REPAIR_REPORT.md.

If QA_STATUS: FAIL, fix reproducible website issues in the isolated workspace. Prioritize
functional blockers first, then responsive/layout issues, accessibility defects, broken links,
and obvious visual inconsistencies. Restart the preview when required, rerun focused checks,
and record each repair plus its verification in {workspace}/REPAIR_REPORT.md.
Finish with REPAIR_STATUS: FIXED or REPAIR_STATUS: BLOCKED.""",
            max_attempts=2,
        ),
        WebsiteStep(
            name="Browser re-verification",
            role="reviewer",
            browser_required=True,
            prompt=f"""{shared}

Re-run browser QA after repair using the preview URL from PREVIEW_REPORT.md. Exercise the same
pages and failures recorded in QA_FAILURES.md and confirm the repaired behavior. Update
{workspace}/QA_REPORT.md with the final browser verification.
End with QA_STATUS: PASS only when the checks were actually performed and passed. Otherwise
end with QA_STATUS: FAIL. Never claim browser verification you could not perform.""",
            max_attempts=2,
        ),
        WebsiteStep(
            name="Final website release review",
            role="reviewer",
            prompt=f"""{shared}

Perform the final website release review. Read WEBSITE_PLAN.md, PREVIEW_REPORT.md,
QA_REPORT.md, QA_FAILURES.md and REPAIR_REPORT.md when present. Check for hard-coded secrets,
unsafe debug settings, missing SEO metadata, broken canonical/robots/sitemap configuration,
obvious accessibility regressions, broken setup instructions, dead routes, insecure forms,
and dependency/configuration mistakes. Fix local issues you can safely fix. Produce:
- {workspace}/RELEASE_CHECKLIST.md
- {workspace}/FINAL_REPORT.md
The final report must state verified checks, unverified checks, remaining blockers and the
preview URL when one was successfully created.""",
        ),
    ]

    return [
        {
            "name": step.name,
            "prompt": step.prompt,
            "model_profile": step.role,
            "role": step.role,
            "max_attempts": step.max_attempts,
            "browser_required": step.browser_required,
        }
        for step in steps
    ]
