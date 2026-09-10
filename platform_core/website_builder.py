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
Preserve existing work when present and improve good work rather than replacing it.
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
            name="Design system and page manifest",
            role="designer",
            prompt=f"""{shared}

Read WEBSITE_PLAN.md. Create two machine-readable files before implementing the UI:
1. {workspace}/DESIGN_SYSTEM.json with a coherent design system containing:
   - color tokens with semantic names
   - typography scale and font choices/fallbacks
   - spacing/radius/shadow/motion tokens
   - reusable UI components and their variants
   - responsive breakpoints
   - button/form/card/navigation patterns
2. {workspace}/SECTION_MANIFEST.json containing an array of sections with stable IDs. Each item must include:
   id, page, name, anchor, selector, description, and sort_order.
3. {workspace}/ASSET_MANIFEST.json containing every planned image/icon/media asset with:
   id, kind, name, path_or_url, alt_text, usage, width, height when known.
Use stable section IDs such as `home.hero`, `home.services`, `about.story` rather than random IDs.
If an asset is missing, record a clear placeholder specification instead of inventing a fake URL.
At the end of your response print exactly these markers followed by compact JSON copies of the three files:
DESIGN_SYSTEM_JSON:
```json
{{...}}
```
SECTION_MANIFEST_JSON:
```json
{{...}}
```
ASSET_MANIFEST_JSON:
```json
{{...}}
```""",
            max_attempts=2,
        ),
        WebsiteStep(
            name="Content and page system",
            role="builder",
            prompt=f"""{shared}

Read WEBSITE_PLAN.md, DESIGN_SYSTEM.json and SECTION_MANIFEST.json. Establish the site's content model and page/component structure.
Create every planned route/page, shared navigation/footer, reusable sections, and stable section IDs matching SECTION_MANIFEST.json.
Do not use lorem ipsum. Write useful realistic copy based on the requirements and clearly mark assumptions.
Keep content easy to edit and prepare the site for real API/content integration when requirements call for it.
Preserve the design tokens and component rules rather than introducing unrelated styles.""",
            max_attempts=2,
        ),
        WebsiteStep(
            name="Visual frontend implementation",
            role="designer",
            prompt=f"""{shared}

Read WEBSITE_PLAN.md, DESIGN_SYSTEM.json, SECTION_MANIFEST.json and ASSET_MANIFEST.json. Build the polished frontend.
Prefer React + Vite + Tailwind CSS when appropriate. Use the generated design tokens consistently.
Implement responsive layouts, strong typography, useful micro-interactions, accessible controls,
mobile navigation, loading/empty/error states where applicable, and real content rather than generic
placeholder cards. Use assets from ASSET_MANIFEST.json deliberately, with descriptive alt text and
performance-conscious sizing. Ensure every navigation link, CTA, form and page is connected.
Each rendered major section must retain its stable section ID in the DOM (for example, id="home.hero")
so later section-level iteration can target it without rewriting unrelated sections.""",
            max_attempts=2,
        ),
        WebsiteStep(
            name="SEO, accessibility and performance hardening",
            role="builder",
            prompt=f"""{shared}

Audit the website against WEBSITE_PLAN.md and DESIGN_SYSTEM.json. Implement page-specific SEO titles/descriptions,
canonical URLs, robots.txt, sitemap.xml, Open Graph/Twitter metadata, favicon/app metadata, and relevant schema.org data.
Add semantic landmarks, heading hierarchy, labels, keyboard focus states, accessible names, contrast-safe UI,
reduced-motion handling where appropriate, and meaningful alt text from ASSET_MANIFEST.json. Remove duplicate metadata,
unused assets and obvious performance problems. Run available build/lint/type checks and fix failures.""",
            max_attempts=2,
        ),
        WebsiteStep(
            name="Integration and preview configuration",
            role="builder",
            prompt=f"""{shared}

Integrate all pages and interactions end-to-end. Remove fake/mock paths that are not needed for the finished website.
Add a clean README, .env.example when configuration is needed, exact local run instructions, and clean startup scripts.
Create {workspace}/APP_PREVIEW.json with the safest preview command, non-privileged port, health_path and cwd.
Keep the preview suitable for sandbox browser verification.""",
            max_attempts=2,
        ),
        WebsiteStep(
            name="Run and preview",
            role="tester",
            prompt=f"""{shared}

Read APP_PREVIEW.json and launch the website inside the isolated sandbox using sandbox_shell in a persistent named session.
Never run it on the host. Curl the configured health_path and inspect startup output. Fix launch/runtime errors.
Then use sandbox_preview with the configured port to obtain the browser-accessible preview URL. Write {workspace}/PREVIEW_REPORT.md with:
- start command
- port and health path
- local health result
- preview URL
- relevant startup logs
- exact command/session needed to stop the preview
Leave the preview running for QA whenever safely possible.""",
            max_attempts=2,
        ),
        WebsiteStep(
            name="Automated website test and repair",
            role="tester",
            prompt=f"""{shared}

Read PREVIEW_REPORT.md and SECTION_MANIFEST.json. Run available frontend tests, build, lint, type checks,
link/accessibility checks and route checks. Verify every planned route builds, stable section IDs exist, assets resolve,
and there are no obvious broken references or console/build errors. Diagnose failures, fix them and rerun the failed checks.
Record the final state in {workspace}/QA_REPORT.md.""",
            max_attempts=3,
        ),
        WebsiteStep(
            name="Browser visual and UX verification",
            role="reviewer",
            browser_required=True,
            prompt=f"""{shared}

Read PREVIEW_REPORT.md, DESIGN_SYSTEM.json, SECTION_MANIFEST.json and ASSET_MANIFEST.json. Perform real browser QA against the running preview URL.
Do not invent a URL. Use sandbox_browser to inspect representative pages and exercise the primary conversion journey.
Check rendering, typography, navigation, CTAs, forms, responsive behavior, asset loading, spacing, hierarchy, consistency,
polish, keyboard/focus basics, and obvious browser/runtime errors.
Before making any repair, call sandbox_browser with action=snapshot and save the returned visual_hash for the representative page
as {workspace}/VISUAL_BASELINE.json. Include the URL, viewport and visual_hash in the file.
Do not silently fix issues in this phase. Record reproducible problems in {workspace}/QA_FAILURES.md and finish with exactly
QA_STATUS: PASS or QA_STATUS: FAIL. If browser tooling is unavailable, report QA_STATUS: FAIL.""",
            max_attempts=2,
        ),
        WebsiteStep(
            name="Autonomous website repair",
            role="fixer",
            prompt=f"""{shared}

Read QA_FAILURES.md, PREVIEW_REPORT.md, DESIGN_SYSTEM.json and SECTION_MANIFEST.json. If QA_STATUS: PASS, make no functional changes;
record that no repair was necessary in {workspace}/REPAIR_REPORT.md.
If QA_STATUS: FAIL, fix reproducible issues in the isolated workspace. Prioritize functional blockers, then responsive/layout issues,
accessibility defects, broken links, asset problems and visual inconsistencies. Do not redesign unrelated sections. Preserve the design
tokens and stable section IDs. Restart the preview when required, rerun focused checks, and record each repair in REPAIR_REPORT.md.
Finish with REPAIR_STATUS: FIXED or REPAIR_STATUS: BLOCKED.""",
            max_attempts=2,
        ),
        WebsiteStep(
            name="Browser re-verification and visual diff",
            role="reviewer",
            browser_required=True,
            prompt=f"""{shared}

Read PREVIEW_REPORT.md, VISUAL_BASELINE.json, QA_FAILURES.md and REPAIR_REPORT.md. Re-run browser QA using the preview URL.
Exercise the same pages and failures and confirm the repaired behavior. Before finishing, call sandbox_browser with action=snapshot
and pass the visual_hash from VISUAL_BASELINE.json as reference_hash. Record the returned visual_diff_score, current visual_hash,
URL and viewport in {workspace}/VISUAL_DIFF_REPORT.json. The score is a deterministic similarity score against the baseline, not a
subjective quality claim. Update QA_REPORT.md with the final browser verification.
End with QA_STATUS: PASS only when the checks were actually performed and passed. Otherwise end with QA_STATUS: FAIL.""",
            max_attempts=2,
        ),
        WebsiteStep(
            name="Final website release review",
            role="reviewer",
            prompt=f"""{shared}

Perform the final website release review. Read WEBSITE_PLAN.md, DESIGN_SYSTEM.json, SECTION_MANIFEST.json, ASSET_MANIFEST.json,
PREVIEW_REPORT.md, QA_REPORT.md, VISUAL_DIFF_REPORT.json and REPAIR_REPORT.md when present. Check for hard-coded secrets,
unsafe debug settings, missing SEO metadata, broken canonical/robots/sitemap configuration, accessibility regressions, dead routes,
broken assets, insecure forms, dependency/configuration mistakes, and unexplained deviations from the generated design system.
Fix local issues you can safely fix. Produce {workspace}/RELEASE_CHECKLIST.md and {workspace}/FINAL_REPORT.md stating verified checks,
unverified checks, visual diff score when available, remaining blockers and preview URL.""",
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
