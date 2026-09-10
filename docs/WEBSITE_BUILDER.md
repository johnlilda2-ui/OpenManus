# OpenManus Website Builder

Website Builder is a specialized mode of the OpenManus AI Builder for production-quality websites.

## What it builds

The mode is optimized for business and company websites, landing pages and marketing sites, portfolios, blogs and content sites, documentation, and responsive multi-page frontend experiences. It can also add a backend/API when dynamic behavior is required.

## Autonomous workflow

Website Builder uses the same durable worker, policy layer, isolated sandbox, artifact store and model router as the general App Builder, with website-specific design and iteration state.

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

Browser phases fail closed: unavailable browser tooling is reported as failed verification rather than a fabricated pass.

## Design system

The builder creates `DESIGN_SYSTEM.json` with semantic color tokens, typography, spacing, radii, shadows, motion, responsive breakpoints, reusable component variants, and UI guidelines. Subsequent implementation and repair phases are instructed to preserve and reuse those tokens.

## Section manifest

The builder creates `SECTION_MANIFEST.json` with stable section IDs such as `home.hero` and `home.services`. Major rendered sections are expected to retain their stable ID in the DOM. The platform persists section metadata so one selected section can be regenerated without rebuilding unrelated sections.

## Asset manifest

The builder creates `ASSET_MANIFEST.json` describing planned images, icons and media, including path/URL, alt text, dimensions when known, and intended usage. Missing user assets are recorded as explicit specifications rather than invented remote URLs. Parsed asset metadata is persisted with the project.

## Live preview and visual verification

The builder creates `APP_PREVIEW.json`, runs the site only inside the isolated sandbox, health-checks it, and obtains a browser-accessible preview URL through `sandbox_preview`.

The sandbox browser now supports a `snapshot` action. It returns a deterministic average-hash and SHA-256 for the captured screenshot. Re-verification can compare the current visual hash against the baseline and report a `visual_diff_score`. This is a deterministic screenshot-similarity signal, not a subjective aesthetic score.

## Section-level iteration

After a Website Builder run completes, a selected section can be regenerated with:

`POST /v1/app-builder/runs/{run_id}/sections/{section_id}/iterate`

The iteration workflow inspects the target section, changes only the necessary files, re-runs the preview, verifies the target section plus an unrelated section, repairs failures, and re-verifies the result.

A dedicated authenticated workspace is available at:

`GET /website-builder`

It displays the live preview, design system, asset manifest, stable sections and per-section **Improve section** actions. During an iteration, the parent website remains the source of truth for the editor while the child run streams its progress.

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

Website Builder uses the existing logical roles: planner, builder, designer, tester, fixer, and reviewer. Assign different configured LLM profiles to those roles through the model-router configuration or `OPENMANUS_MODEL_*` environment overrides. No vendor credentials are stored in the repository.

## Delivery

The final site is packaged as `application.zip` with the platform's artifact integrity metadata. Real AI generation requires an LLM provider; production sandbox/browser execution requires an isolated Daytona environment.
