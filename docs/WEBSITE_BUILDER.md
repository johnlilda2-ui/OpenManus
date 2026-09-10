# OpenManus Website Builder

Website Builder is a specialized mode of the OpenManus AI Builder for production-quality websites.

## What it builds

The mode is optimized for:

- business and company websites
- landing pages and marketing sites
- portfolios
- blogs and content sites
- documentation and informational sites
- responsive multi-page frontend experiences

It can also add a backend/API when the requirements need dynamic behavior.

## Autonomous workflow

Website Builder uses the same durable worker, policy layer, isolated sandbox, artifact store and model router as the general App Builder, with additional website-specific design and iteration state.

The workflow is:

1. Website strategy and information architecture
2. Design system and page/section/asset manifest generation
3. Content and page system
4. Visual frontend implementation using stable section IDs
5. SEO, accessibility and performance hardening
6. Integration and preview configuration
7. Run and preview in the isolated sandbox
8. Automated website testing and repair
9. Browser visual/UX verification with a deterministic visual snapshot baseline
10. Autonomous website repair
11. Browser re-verification with visual similarity/diff scoring
12. Final website security and release review

The browser phases are fail-closed: unavailable browser tooling is reported as a failed verification rather than a fabricated pass.

## Design system

The builder creates `DESIGN_SYSTEM.json` containing semantic color tokens, typography, spacing, radii, shadows, motion, responsive breakpoints, reusable component variants, and UI guidelines. Subsequent frontend and repair phases are instructed to preserve and reuse these tokens rather than introduce unrelated styles.

## Section manifest

The builder creates `SECTION_MANIFEST.json` with stable section IDs such as `home.hero` and `home.services`. Each major rendered section is expected to retain its stable ID in the DOM. The platform stores the parsed section metadata so individual sections can be targeted later without rebuilding the entire site.

## Asset manifest

The builder creates `ASSET_MANIFEST.json` describing planned images, icons and media, including paths or URLs, alt text, dimensions when known, and intended usage. Missing user assets are recorded as explicit specifications rather than invented remote URLs. The parsed asset metadata is persisted with the project.

## Live preview and visual verification

The builder creates `APP_PREVIEW.json`, runs the website only inside the isolated sandbox, health-checks it, and obtains a browser-accessible preview URL through `sandbox_preview`.

Browser verification uses the sandbox browser and a deterministic screenshot hash. The final re-verification compares that hash against the recorded baseline and reports a `visual_diff_score`. This is a similarity signal for the captured screenshot, not a subjective claim that the website is aesthetically perfect.

## Section-level iteration

After a website run is complete, a specific section can be regenerated with:

`POST /v1/app-builder/runs/{run_id}/sections/{section_id}/iterate`

The iteration workflow inspects the target section, changes only the necessary files, re-runs the preview, verifies the target section plus an unrelated section, performs repair when needed, and re-verifies the result.

The dedicated workspace is available at:

`GET /website-builder`

It displays the live preview, parsed design system, assets, stable sections and per-section **Improve section** actions.

## API

Create a website run with:

`POST /v1/projects/{project_id}/website-builder`

Example request body:

```json
{
  "name": "Acme Logistics Website",
  "requirements": "Build a modern logistics company website with Home, About, Services, Fleet, Contact and quote request form. Include strong SEO metadata, responsive mobile navigation, accessible UI, polished animations and a professional visual design."
}
```

The response contains the workflow, durable run ID, workspace and `mode: "website"`.

The existing App Builder endpoint also supports explicit `mode: "website"` for integrations that prefer one common route.

## Model routing

Website Builder uses the logical roles already provided by the platform:

- planner
- builder
- designer
- tester
- fixer
- reviewer

Assign different configured LLM profiles to those roles through the existing model-router configuration or `OPENMANUS_MODEL_*` environment overrides.

No vendor credentials are stored in the repository.

## Preview and delivery

The final application is packaged as `application.zip` with the platform's existing artifact integrity metadata. External LLM credentials are required for real generation, and production sandbox/browser execution requires a configured isolated Daytona environment.
