from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WebsiteStep:
    name: str
    role: str
    prompt: str
    max_attempts: int = 1
    browser_required: bool = False


def build_simple_static_files(requirements: str) -> dict[str, str]:
    """Return a polished, dependency-free one-page site for the fast static path."""
    return {
        "index.html": """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="A clean, modern personal portfolio website.">
  <title>Personal Portfolio</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <header class="site-header">
    <nav class="nav container" aria-label="Primary">
      <a class="brand" href="#home">Portfolio</a>
      <button class="nav-toggle" type="button" aria-expanded="false" aria-controls="nav-links">Menu</button>
      <div class="nav-links" id="nav-links">
        <a href="#about">About</a>
        <a href="#projects">Projects</a>
        <a href="#contact">Contact</a>
      </div>
    </nav>
  </header>

  <main>
    <section id="home" class="hero">
      <div class="container hero-grid">
        <div class="hero-copy">
          <p class="eyebrow">Personal Portfolio</p>
          <h1>Build work that is simple, useful, and memorable.</h1>
          <p class="hero-text">A clean starting point for presenting your work, your story, and the next project you want people to discover.</p>
          <div class="hero-actions">
            <a class="button primary" href="#projects">View projects</a>
            <a class="button secondary" href="#contact">Get in touch</a>
          </div>
        </div>
        <div class="hero-card" aria-hidden="true">
          <span class="orb orb-one"></span>
          <span class="orb orb-two"></span>
          <div class="hero-card-inner">
            <span class="hero-card-label">Selected work</span>
            <strong>Thoughtful digital experiences</strong>
          </div>
        </div>
      </div>
    </section>

    <section id="about" class="section">
      <div class="container two-col">
        <div>
          <p class="eyebrow">About</p>
          <h2>A clear introduction without the clutter.</h2>
        </div>
        <div class="section-copy">
          <p>Use this section to introduce yourself, explain what you do, and describe the kind of work you enjoy.</p>
          <p>Replace this placeholder text with your own background, skills, interests, or professional story.</p>
        </div>
      </div>
    </section>

    <section id="projects" class="section section-alt">
      <div class="container">
        <div class="section-heading">
          <div>
            <p class="eyebrow">Projects</p>
            <h2>Selected work</h2>
          </div>
          <p>Three flexible cards ready for your real projects.</p>
        </div>
        <div class="project-grid">
          <article class="project-card">
            <div class="project-number">01</div>
            <h3>Project One</h3>
            <p>Add a short description of the problem, your approach, and the result.</p>
            <a href="#contact" aria-label="Discuss Project One">Discuss project →</a>
          </article>
          <article class="project-card">
            <div class="project-number">02</div>
            <h3>Project Two</h3>
            <p>Highlight the idea, technology, design decision, or lesson that made this work meaningful.</p>
            <a href="#contact" aria-label="Discuss Project Two">Discuss project →</a>
          </article>
          <article class="project-card">
            <div class="project-number">03</div>
            <h3>Project Three</h3>
            <p>Replace this copy with accurate project details, outcomes, and links you control.</p>
            <a href="#contact" aria-label="Discuss Project Three">Discuss project →</a>
          </article>
        </div>
      </div>
    </section>

    <section id="contact" class="section contact-section">
      <div class="container contact-card">
        <div>
          <p class="eyebrow">Contact</p>
          <h2>Have a project in mind?</h2>
          <p>Use the form to create a simple contact experience, then connect it to your preferred email or backend later.</p>
        </div>
        <form id="contact-form" class="contact-form">
          <label for="name">Name</label>
          <input id="name" name="name" autocomplete="name" placeholder="Your name" required>
          <label for="email">Email</label>
          <input id="email" name="email" type="email" autocomplete="email" placeholder="your-email@example.com" required>
          <label for="message">Message</label>
          <textarea id="message" name="message" rows="5" placeholder="Tell me a little about the project." required></textarea>
          <button class="button primary" type="submit">Send message</button>
          <p id="form-status" class="form-status" role="status" aria-live="polite"></p>
        </form>
      </div>
    </section>
  </main>

  <footer class="site-footer">
    <div class="container footer-inner">
      <span>© <span id="year"></span> Portfolio</span>
      <a href="#home">Back to top ↑</a>
    </div>
  </footer>
  <script src="script.js"></script>
</body>
</html>
""",
        "styles.css": """*{box-sizing:border-box}
:root{--bg:#0b1020;--surface:#121a2c;--surface-2:#18233a;--text:#f5f7fb;--muted:#aab4c8;--accent:#7c9cff;--accent-2:#9d7cff;--line:rgba(255,255,255,.1);--max:1120px}
html{scroll-behavior:smooth}
body{margin:0;font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:linear-gradient(180deg,var(--bg),#0e1527 45%,#0b1020);color:var(--text);line-height:1.6}
a{color:inherit;text-decoration:none}
.container{width:min(100% - 40px,var(--max));margin-inline:auto}
.site-header{position:sticky;top:0;z-index:20;background:rgba(11,16,32,.78);backdrop-filter:blur(14px);border-bottom:1px solid var(--line)}
.nav{min-height:72px;display:flex;align-items:center;justify-content:space-between;gap:24px}
.brand{font-weight:800;letter-spacing:.02em}
.nav-links{display:flex;gap:24px}
.nav-links a{color:var(--muted);transition:color .2s ease}
.nav-links a:hover,.nav-links a:focus-visible{color:var(--text)}
.nav-toggle{display:none;background:none;border:1px solid var(--line);color:var(--text);border-radius:999px;padding:8px 13px}
.hero{padding:96px 0 88px}
.hero-grid{display:grid;grid-template-columns:1.1fr .9fr;gap:56px;align-items:center}
.eyebrow{text-transform:uppercase;letter-spacing:.16em;font-size:.75rem;color:var(--accent);font-weight:800;margin:0 0 12px}
h1,h2,h3{line-height:1.1;margin:0 0 18px}
h1{font-size:clamp(3rem,7vw,5.8rem);max-width:10ch}
h2{font-size:clamp(2rem,4vw,3.25rem)}
h3{font-size:1.45rem}
.hero-text,.section-copy p,.section-heading>p,.contact-card p{color:var(--muted);max-width:62ch}
.hero-actions{display:flex;gap:12px;flex-wrap:wrap;margin-top:28px}
.button{display:inline-flex;align-items:center;justify-content:center;border:1px solid var(--line);border-radius:14px;padding:12px 18px;font-weight:750;cursor:pointer}
.button.primary{background:linear-gradient(135deg,var(--accent),var(--accent-2));border-color:transparent;color:#0a0d18}
.button.secondary{background:rgba(255,255,255,.04)}
.hero-card{min-height:420px;border:1px solid var(--line);border-radius:32px;position:relative;overflow:hidden;background:radial-gradient(circle at 30% 30%,rgba(124,156,255,.3),transparent 34%),radial-gradient(circle at 75% 75%,rgba(157,124,255,.25),transparent 30%),var(--surface)}
.hero-card-inner{position:absolute;inset:auto 24px 24px;padding:22px;border:1px solid var(--line);border-radius:24px;background:rgba(11,16,32,.72);backdrop-filter:blur(10px)}
.hero-card-label{display:block;color:var(--muted);font-size:.85rem;margin-bottom:8px}
.hero-card-inner strong{font-size:1.3rem}
.orb{position:absolute;width:170px;height:170px;border-radius:50%;filter:blur(2px);opacity:.65}
.orb-one{top:58px;right:70px;background:linear-gradient(135deg,var(--accent),transparent)}
.orb-two{bottom:120px;left:70px;background:linear-gradient(135deg,var(--accent-2),transparent)}
.section{padding:100px 0}
.section-alt{background:rgba(255,255,255,.025);border-block:1px solid var(--line)}
.two-col{display:grid;grid-template-columns:.85fr 1.15fr;gap:56px}
.section-copy{padding-top:10px}
.section-heading{display:flex;justify-content:space-between;gap:40px;align-items:end;margin-bottom:34px}
.project-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}
.project-card{min-height:290px;padding:26px;border:1px solid var(--line);border-radius:24px;background:linear-gradient(180deg,rgba(255,255,255,.04),rgba(255,255,255,.015));display:flex;flex-direction:column}
.project-number{color:var(--accent);font-size:.8rem;font-weight:800;letter-spacing:.12em;margin-bottom:auto}
.project-card p{color:var(--muted);margin-bottom:28px}
.project-card a{color:var(--text);font-weight:700}
.contact-section{padding-top:72px}
.contact-card{display:grid;grid-template-columns:.95fr 1.05fr;gap:48px;padding:34px;border:1px solid var(--line);border-radius:28px;background:var(--surface)}
.contact-form{display:grid;gap:10px}
.contact-form label{font-size:.9rem;font-weight:700}
.contact-form input,.contact-form textarea{width:100%;border:1px solid var(--line);border-radius:14px;padding:13px 14px;background:#0c1324;color:var(--text);font:inherit;outline:none}
.contact-form input:focus,.contact-form textarea:focus{border-color:var(--accent);box-shadow:0 0 0 4px rgba(124,156,255,.12)}
.form-status{min-height:1.4em;margin:0!important}
.site-footer{border-top:1px solid var(--line);padding:24px 0;color:var(--muted)}
.footer-inner{display:flex;justify-content:space-between;gap:16px}
@media (max-width:820px){
  .nav-toggle{display:block}
  .nav-links{display:none;position:absolute;left:20px;right:20px;top:64px;padding:14px;border:1px solid var(--line);border-radius:18px;background:#0e1628;flex-direction:column}
  .nav-links.open{display:flex}
  .hero{padding-top:72px}.hero-grid,.two-col,.contact-card{grid-template-columns:1fr}
  .project-grid{grid-template-columns:1fr}
  .section-heading{display:block}
  .hero-card{min-height:320px}
}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}.nav-links a,.button{transition:none}}
""",
        "script.js": """const toggle=document.querySelector('.nav-toggle');
const links=document.querySelector('#nav-links');
const form=document.querySelector('#contact-form');
const status=document.querySelector('#form-status');
const year=document.querySelector('#year');

if(year) year.textContent=new Date().getFullYear();

toggle?.addEventListener('click',()=>{
  const open=links.classList.toggle('open');
  toggle.setAttribute('aria-expanded',String(open));
});

links?.querySelectorAll('a').forEach(link=>{
  link.addEventListener('click',()=>{
    links.classList.remove('open');
    toggle?.setAttribute('aria-expanded','false');
  });
});

form?.addEventListener('submit',event=>{
  event.preventDefault();
  status.textContent='Thanks — the form is ready to connect to your preferred email or backend.';
  form.reset();
});
""",
    }


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

    normalized = requirements.lower()
    simple_static = (
        "SIMPLE_STATIC_WEBSITE"
        if (
            "one-page" in normalized
            and ("plain html" in normalized or "html/css/javascript" in normalized or "html/css/js" in normalized)
            and not any(term in normalized for term in ("marketplace", "e-commerce", "ecommerce", "saas", "booking", "dashboard", "database", "authentication"))
        )
        else None
    )
    if simple_static:
        return [
            {
                "name": "Build, preview and verify simple website",
                "prompt": f"""{shared}

This is a SIMPLE_STATIC_WEBSITE request. Do not run the long research/design/QA pipeline. Finish this request in a maximum of 4 internal AI work cycles. Build the requested one-page website directly in the project root using only plain HTML, CSS and JavaScript.

Create exactly these files unless genuinely needed otherwise: index.html, styles.css, script.js. Make the page polished, responsive, accessible, and visually coherent. Implement the requested hero, About, three project cards, and contact section. Do not invent real people's identities, real client claims, or fake external project URLs. Use safe local placeholders for links.

After creating the files, launch a simple local server INSIDE the Daytona sandbox on port 8081 with the project directory as the document root. Do not use port 8080: Daytona already runs an internal FastAPI/static service on that port. Use one persistent server command, verify the three files with curl, then call the sandbox preview tool for port 8081 and capture its browser-accessible URL. Do not spend extra cycles on research, refactoring, or optional QA. Leave the preview running.

Use these exact checks:
- cd to {workspace}
- python -m http.server 8081 --bind 0.0.0.0
- curl --noproxy '*' -fsS http://127.0.0.1:8081/
- curl --noproxy '*' -fsS http://127.0.0.1:8081/styles.css
- curl --noproxy '*' -fsS http://127.0.0.1:8081/script.js
- call sandbox_preview with port 8081

Return exactly:
PREVIEW_URL: <the real preview URL>
WEBSITE_READY: true
""",
                "model_profile": "builder",
                "role": "builder",
                "max_attempts": 1,
                "max_agent_steps": 4,
                "execution_mode": "deterministic_static",
                "browser_required": False,
            }
        ]

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
