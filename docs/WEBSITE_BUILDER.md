# OpenManus Website Builder

Website Builder is a specialized mode of the OpenManus AI Builder for production-quality websites.

## What it builds

The mode is optimized for business and company websites, landing pages and marketing sites, portfolios, blogs and content sites, documentation, marketplaces, and responsive multi-page frontend experiences. It can also add a backend/API when dynamic behavior is required.

## Research-driven design

Before implementation, Website Builder classifies the request and researches the public web for **exactly 1 or 2** relevant design/UX references. For a marketplace request, it specifically looks for patterns around discovery, search, categories, filters, listing cards, seller identity, trust signals, and buyer/seller journeys.

The research is stored in `WEBSITE_RESEARCH.md` and `WEBSITE_RESEARCH.json`, then used to inform the site's information architecture and original design system. References are treated as inspiration and benchmarking only. The agent is instructed not to copy proprietary text, images, logos, trademarks, exact layouts, or branded identity. If search is unavailable, the build records that limitation and continues with general design knowledge rather than inventing URLs.

The operational workspace shows the selected references and their URLs so the user can see what informed the design.

## Autonomous workflow

Website Builder uses the same durable worker, policy layer, isolated sandbox, artifact store and model router as the general App Builder, with website-specific design and iteration state.

1. Reference research and design inspiration
2. Website strategy and information architecture
3. Design system and page/section/asset manifest generation
4. Content and page system
5. Visual asset creation and sourcing
6. Visual frontend implementation
7. SEO, accessibility and performance hardening
8. Integration and preview configuration
9. Run and preview in the isolated sandbox
10. Automated website testing and repair
11. Browser visual/UX verification with deterministic visual snapshot baselines
12. Autonomous website repair
13. Browser re-verification with visual similarity/diff scoring
14. Final website security and release review

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

It displays the live preview, research references, design system, asset manifest, stable sections and per-section **Improve section** actions. During an iteration, the parent website remains the editor's source of truth while the child run streams its progress.

## Marketplace-specific behavior

When someone says something like **“build a marketplace for me”**, the builder is instructed to recognize the marketplace model and research 1–2 suitable public references before designing. It then uses the references to inform an original marketplace experience with patterns such as:

- strong discovery and category navigation
- useful search and filtering
- high-quality listing/product cards
- clear seller identity and trust information
- buyer and seller journeys that do not compete with each other
- responsive mobile browsing
- focused calls to action and conversion paths

These patterns align with current marketplace UX research emphasizing the distinct needs of buyers and sellers and the importance of trust, discovery, and filtering. 

## API

Create a website run with:

`POST /v1/projects/{project_id}/website-builder`

Example request body:

```json
{
  "name": "Acme Marketplace",
  "requirements": "Build a premium marketplace for independent artisans with discovery, categories, search, filters, listing cards, seller profiles, trust signals, favorites, and responsive buyer/seller journeys."
}
```

The response contains the workflow, durable run ID, workspace and `mode: "website"`.

## Model routing

Website Builder uses the existing logical roles: planner, builder, designer, tester, fixer, and reviewer. Assign different configured LLM profiles to those roles through the model-router configuration or `OPENMANUS_MODEL_*` environment overrides. No vendor credentials are stored in the repository.

## Delivery

The final site is packaged as `application.zip` with the platform's artifact integrity metadata. Real AI generation requires an LLM provider; production sandbox/browser execution requires an isolated Daytona environment.
