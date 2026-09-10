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
            name="Reference research and design inspiration",
            role="planner",
            prompt=f"""{shared}

First classify the website request (for example marketplace, ecommerce, SaaS, portfolio, booking,
service marketplace, publication, or business site). Research the public web for exactly 1 or 2
strong reference sites that are relevant to this request and useful for visual/UX inspiration.

Use the sandboxed `web_search` tool. Prefer established public sites and design/UX case studies that
are relevant to the requested business model. For marketplace requests specifically, look for examples
that demonstrate discovery/search, category navigation, filters, product/listing cards, seller identity,
trust signals, and buyer/seller journeys. Select references because their patterns are useful, not merely
because they are famous.

Do not copy proprietary text, images, logos, trademarks, exact layouts, or branded visual identity.
Extract reusable design principles and interaction patterns in your own words. Treat every source as
inspiration and a benchmark, not a template to clone.

Create {workspace}/WEBSITE_RESEARCH.md and {workspace}/WEBSITE_RESEARCH.json containing:
- detected website type
- research queries
- 1 or 2 selected references with name, URL, category, reason_selected
- observed UX patterns
- observed visual patterns
- marketplace-specific patterns when relevant
- opportunities to differentiate the new website
- explicit note that the references are inspiration only

At the end of the response print:
WEBSITE_RESEARCH_JSON:
```json
{{"website_type":"...","references":[{{"name":"...","url":"...","category":"...","reason_selected":"..."}}],"patterns":{{"ux":[],"visual":[],"trust":[],"navigation":[]}},"differentiation":[]}}
```
If web search is unavailable, record `search_status: unavailable` and continue using general design knowledge; never invent reference URLs.""",
            max_attempts=2,
        ),
        WebsiteStep(
            name="Website strategy and information architecture",
            role="planner",
            prompt=f"""{shared}

Read WEBSITE_RESEARCH.md when present. Analyze the requirements and create {workspace}/WEBSITE_PLAN.md containing:
- target audience and primary conversion goal
- sitemap/page list and navigation hierarchy
- content sections and calls to action for every page
- design direction informed by research patterns without copying any reference
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

Read WEBSITE_RESEARCH.md and WEBSITE_PLAN.md. Translate useful reference patterns into an original design system.
Create two machine-readable files before implementing the UI:
1. {workspace}/DESIGN_SYSTEM.json with coherent semantic color, typography, spacing, radius, shadow, motion,
component, breakpoint, button/form/card/navigation tokens. Include a short `research_influences` section describing
patterns borrowed conceptually, never copied visually.
2. {workspace}/SECTION_MANIFEST.json containing stable section IDs. Each item must include id, page, name, anchor,
selector, description, and sort_order.
3. {workspace}/ASSET_MANIFEST.json containing every planned image/icon/media asset with id, kind, name, path_or_url,
alt_text, usage, width, height when known, and `license_or_source` when using an external asset.
Use IDs such as `home.hero`, `home.categories`, `home.featured-listings`, `listing.results`, `listing.filters`,
`listing.trust`, `seller.profile` rather than random IDs.
If an asset is missing, record a clear placeholder specification instead of inventing a fake URL.""",
            max_attempts=2,
        ),
        WebsiteStep(
            name="Content and page system",
            role="builder",
            prompt=f"""{shared}

Read WEBSITE_PLAN.md, DESIGN_SYSTEM.json, SECTION_MANIFEST.json and WEBSITE_RESEARCH.md. Establish the content model
and page/component structure. Create every planned route/page, shared navigation/footer, reusable sections, and stable
section IDs matching SECTION_MANIFEST.json. Do not use lorem ipsum. Write useful realistic copy based on the requirements
and clearly mark assumptions. Keep content easy to edit and preserve the generated design tokens.""",
            max_attempts=2,
        ),
        WebsiteStep(
            name="Visual asset creation and sourcing",
            role="designer",
            prompt=f"""{shared}

Read ASSET_MANIFEST.json and DESIGN_SYSTEM.json. Create the site's visual asset kit inside the project where practical.
Prefer original local SVG illustrations, icons, decorative backgrounds, gradients, subtle patterns, and CSS-based art
when a custom graphic is needed and no image-generation provider is configured. For photographic assets, only use
assets already supplied by the user or sources that are explicitly marked as permitted/licensed; record the source in
ASSET_MANIFEST.json. Never scrape or hotlink random commercial imagery merely to imitate a reference site.
Optimize images, provide useful dimensions and alt text, and keep filenames stable so later section iteration does not break them.
Update ASSET_MANIFEST.json and produce {workspace}/ASSET_REPORT.md with created assets, sourced assets, missing assets,
and any license/source notes.""",
            max_attempts=2,
        ),
        WebsiteStep(
            name="Visual frontend implementation",
            role="designer",
            prompt=f"""{shared}

Read WEBSITE_RESEARCH.md, WEBSITE_PLAN.md, DESIGN_SYSTEM.json, SECTION_MANIFEST.json and ASSET_MANIFEST.json.
Build the polished frontend using the original design system informed by the research. Prefer React + Vite + Tailwind
CSS when appropriate. Implement responsive layouts, strong typography, meaningful micro-interactions, accessible controls,
mobile navigation, loading/empty/error states, and real content. Use the generated/sourced assets deliberately. Ensure
navigation, CTAs, forms, search/filter interactions and major marketplace journeys are connected when applicable.
Every major section must retain its stable ID in the DOM so later iteration can target it precisely.""",
            max_attempts=2,
        ),
        WebsiteStep(
            name="SEO, accessibility and performance hardening",
            role="builder",
            prompt=f"""{shared}

Audit the website against WEBSITE_PLAN.md, DESIGN_SYSTEM.json, ASSET_MANIFEST.json and WEBSITE_RESEARCH.md. Implement
page-specific SEO titles/descriptions, canonical URLs, robots.txt, sitemap.xml, Open Graph/Twitter metadata, favicon/app
metadata and relevant schema.org data. Add semantic landmarks, heading hierarchy, labels, keyboard focus states,
accessible names, contrast-safe UI, reduced-motion handling, meaningful alt text, responsive images, lazy loading where
appropriate, and a clean loading strategy. Run available build/lint/type checks and fix failures.""",
            max_attempts=2,
        ),
        WebsiteStep(
            name="Integration and preview configuration",
            role="builder",
            prompt=f"""{shared}

Integrate all pages and interactions end-to-end. For marketplace-style sites, verify buyer discovery, search, filters,
listing details, seller/trust information, and primary conversion actions form a coherent journey. Remove fake/mock paths
that are not needed for the finished website. Add a clean README, .env.example when configuration is needed, exact local
run instructions, and clean startup scripts. Create {workspace}/APP_PREVIEW.json with the safest preview command,
non-privileged port, health_path and cwd.""",
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

Read PREVIEW_REPORT.md, SECTION_MANIFEST.json and ASSET_MANIFEST.json. Run available frontend tests, build, lint, type,
link/accessibility checks and route checks. Verify every planned route builds, stable section IDs exist, assets resolve,
and there are no obvious broken references or console/build errors. Diagnose failures, fix them and rerun failed checks.
Record the final state in {workspace}/QA_REPORT.md.""",
            max_attempts=3,
        ),
        WebsiteStep(
            name="Browser visual and UX verification",
            role="reviewer",
            browser_required=True,
            prompt=f"""{shared}

Read PREVIEW_REPORT.md, WEBSITE_RESEARCH.md, DESIGN_SYSTEM.json, SECTION_MANIFEST.json and ASSET_MANIFEST.json.
Perform real browser QA against the running preview URL. Inspect representative pages and the primary conversion journey.
Check rendering, typography, navigation, search/filter interactions when applicable, CTAs, forms, responsive behavior,
asset loading, spacing, hierarchy, consistency, trust signals for marketplaces, keyboard/focus basics, and browser/runtime errors.
Before repair, call sandbox_browser action=snapshot for each representative page and save the returned visual_hash values in
{workspace}/VISUAL_BASELINE.json with URL and viewport. Do not silently fix issues. Record reproducible problems in
{workspace}/QA_FAILURES.md and finish with exactly QA_STATUS: PASS or QA_STATUS: FAIL. If browser tooling is unavailable, report FAIL.""",
            max_attempts=2,
        ),
        WebsiteStep(
            name="Autonomous website repair",
            role="fixer",
            prompt=f"""{shared}

Read QA_FAILURES.md, PREVIEW_REPORT.md, DESIGN_SYSTEM.json, SECTION_MANIFEST.json, WEBSITE_RESEARCH.md and ASSET_MANIFEST.json.
If QA_STATUS: PASS, make no functional changes; record that no repair was necessary. If FAIL, fix reproducible issues
inside the isolated workspace. Prioritize functional blockers, then responsive/layout issues, accessibility defects,
broken links, asset problems and visual inconsistencies. Do not redesign unrelated sections and do not copy reference-site
branding. Preserve design tokens and stable section IDs. Restart preview when required and record repairs.""",
            max_attempts=2,
        ),
        WebsiteStep(
            name="Browser re-verification and visual diff",
            role="reviewer",
            browser_required=True,
            prompt=f"""{shared}

Read PREVIEW_REPORT.md, VISUAL_BASELINE.json, QA_FAILURES.md, REPAIR_REPORT.md and WEBSITE_RESEARCH.md. Re-run browser QA.
Exercise the same pages and failures and confirm repaired behavior. Call sandbox_browser action=snapshot with each baseline
reference_hash where available. Record current visual_hash, visual_diff_score, URL and viewport for every page in
{workspace}/VISUAL_DIFF_REPORT.json. These scores are deterministic similarity measurements against prior snapshots,
not a subjective claim of quality. Update QA_REPORT.md and finish with QA_STATUS: PASS only when the checks were actually performed and passed.""",
            max_attempts=2,
        ),
        WebsiteStep(
            name="Final website release review",
            role="reviewer",
            prompt=f"""{shared}

Perform the final website release review. Read WEBSITE_RESEARCH.md, WEBSITE_PLAN.md, DESIGN_SYSTEM.json, SECTION_MANIFEST.json,
ASSET_MANIFEST.json, ASSET_REPORT.md, PREVIEW_REPORT.md, QA_REPORT.md, VISUAL_DIFF_REPORT.json and REPAIR_REPORT.md when present.
Check for hard-coded secrets, unsafe debug settings, missing SEO metadata, broken canonical/robots/sitemap configuration,
accessibility regressions, dead routes, broken assets, insecure forms, dependency/configuration mistakes, and unexplained
deviations from the design system. Confirm external reference sites were used only as inspiration and that no proprietary
content or branding was copied. Fix local issues you can safely fix. Produce RELEASE_CHECKLIST.md and FINAL_REPORT.md with
verified checks, unverified checks, visual diff scores when available, remaining blockers, preview URL, and final asset/source notes.""",
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
