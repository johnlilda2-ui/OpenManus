# OpenManus Website Builder

Website Builder is a specialized mode of the OpenManus AI Builder for production-quality websites.

## What it builds

The mode is optimized for business and company websites, landing pages and marketing sites, portfolios, blogs and content sites, documentation, marketplaces, and responsive multi-page frontend experiences. It can also add a backend/API when dynamic behavior is required.

## Pre-build design selection

Before full implementation, the Website Builder provides a design-selection stage. A lightweight research task classifies the request and uses the available web-search/browser tools to find **exactly 1 or 2** relevant public design/UX references when live search is available. For marketplace requests, research focuses on discovery, search, categories, filters, listing cards, seller identity, trust signals, and buyer/seller journeys.

The user then receives up to **three selectable design directions**:

- **Reference design 1** — a visual inspiration board derived from the first researched site, with the original source link and extracted design/UX patterns.
- **Reference design 2** — shown when a second strong reference is found, with its source link and extracted patterns.
- **Original OpenManus concept** — an independent design direction generated from the user's requirements rather than copied from a reference.

The reference cards are intentionally design boards rather than copied website screenshots. This keeps the builder focused on reusable visual/UX ideas while linking users to the real public source for inspection. The agent is instructed not to copy proprietary text, images, logos, trademarks, source code, exact layouts, or branded identity.

The chosen option becomes a `SELECTED_DESIGN_DIRECTION` directive for the real Website Builder run. Reference selections remain inspiration-only; the implementation remains original and faithful to the user's requirements.

If search is unavailable, the design task records that limitation without inventing URLs and the original OpenManus concept remains available for selection.

## Research-driven design

After selection, the full Website Builder still performs its own research-informed planning so the selected direction is combined with the site's actual information architecture, content, accessibility, SEO, and functional requirements.

Research is stored in `WEBSITE_RESEARCH.md` and `WEBSITE_RESEARCH.json`. The build creates a coherent original design system rather than cloning a source site.

## Autonomous workflow

After the user selects a design direction, Website Builder uses the same durable worker, policy layer, isolated sandbox, artifact store and model router as the general App Builder, with website-specific design and iteration state.

1. User requests website and starts design research
2. Pre-build gallery returns 1–2 researched references plus 1 original concept
3. User selects a design direction
4. Reference research and design inspiration during the build
5. Website strategy and information architecture
6. Design system and page/section/asset manifest generation
7. Content and page system
8. Visual asset creation and sourcing
9. Visual frontend implementation
10. SEO, accessibility and performance hardening
11. Integration and preview configuration
12. Run and preview in the isolated sandbox
13. Automated website testing and repair
14. Browser visual/UX verification with deterministic visual snapshot baselines
15. Autonomous website repair
16. Browser re-verification with visual similarity/diff scoring
17. Final website security and release review

Browser phases fail closed: unavailable browser tooling is reported as failed verification rather than a fabricated pass.

## Design system

The builder creates `DESIGN_SYSTEM.json` with semantic color tokens, typography, spacing, radii, shadows, motion, responsive breakpoints, reusable component variants, UI guidelines, and research influences expressed as abstract patterns rather than copied branding.

## Sections

The builder creates `SECTION_MANIFEST.json` with stable section IDs such as `home.hero`, `home.categories`, `home.featured-listings`, `listing.filters`, and `seller.profile`. Major rendered sections are expected to retain their stable ID in the DOM. The platform persists section metadata so one selected section can be regenerated without rebuilding unrelated sections.

## Assets

The builder creates `ASSET_MANIFEST.json` for images, icons and media. When custom graphics are needed and no image provider is configured, it can generate original local SVG/CSS assets and keep them inside the project. For photographic assets, it prefers user-provided or explicitly permitted/licensed sources and records source/license information. It does not hotlink arbitrary commercial imagery merely to imitate a reference site.

## Live preview and visual verification

The builder creates `APP_PREVIEW.json`, runs the site only inside the isolated sandbox, health-checks it, and obtains a browser-accessible preview URL through `sandbox_preview`.

The sandbox browser supports a `snapshot` action that returns a deterministic visual hash and screenshot hash. Re-verification compares a later snapshot to a stored baseline and reports a `visual_diff_score`. This is an objective screenshot-similarity signal, not a subjective aesthetic score.

## Section-level iteration

After a Website Builder run completes, a selected section can be regenerated with:

`POST /v1/app-builder/runs/{run_id}/sections/{section_id}/iterate`

The iteration workflow inspects the target section, changes only the necessary files, re-runs the preview, verifies the target section plus an unrelated section, repairs failures, and re-verifies the result while preserving the existing research-informed design system.

The dedicated authenticated workspace is available at:

`GET /website-builder`

It displays the pre-build design gallery, live preview, research references, design system, asset manifest, stable sections and per-section **Improve section** actions. During an iteration, the parent website remains the editor's source of truth while the child run streams its progress.

## Marketplace-specific behavior

When someone says something like **“build a marketplace for me”**, the builder is instructed to recognize the marketplace model and research 1–2 suitable public references before designing. It then uses the selected direction and research to inform an original marketplace experience with patterns such as:

- strong discovery and category navigation
- useful search and filtering
- high-quality listing/product cards
- clear seller identity and trust information
- buyer and seller journeys that do not compete with each other
- responsive mobile browsing
- focused calls to action and conversion paths

## API

Create a website run with:

`POST /v1/projects/{project_id}/website-builder`

The response contains the workflow, durable run ID, workspace and `mode: "website"`.

The design gallery itself uses the existing authenticated task API for the lightweight pre-build research step. Once a design is selected in the workspace, the selected direction is included in the real Website Builder requirements.

## Model routing

Website Builder uses the existing logical roles: planner, builder, designer, tester, fixer, and reviewer. Assign different configured LLM profiles to those roles through the model-router configuration or `OPENMANUS_MODEL_*` environment overrides. No vendor credentials are stored in the repository.

## Delivery

The final site is packaged as `application.zip` with the platform's artifact integrity metadata. Real AI generation requires an LLM provider; production sandbox/browser execution requires an isolated Daytona environment.
