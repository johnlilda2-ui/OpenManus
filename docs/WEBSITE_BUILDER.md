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

Website Builder uses the same durable worker, policy layer, isolated sandbox, artifact store and model router as the general App Builder.

The workflow is:

1. Website strategy and information architecture
2. Content and page system
3. Visual frontend implementation
4. SEO, accessibility and performance hardening
5. Integration and preview configuration
6. Run and preview in the isolated sandbox
7. Automated website testing and repair
8. Browser visual/UX verification
9. Autonomous website repair
10. Browser re-verification
11. Final website release review

The browser phases are fail-closed: unavailable browser tooling is reported as a failed verification rather than a fabricated pass.

## API

Use the dedicated endpoint:

`POST /v1/projects/{project_id}/website-builder`

Example request body:

```json
{
  "name": "Acme Logistics Website",
  "requirements": "Build a modern logistics company website with Home, About, Services, Fleet, Contact and quote request form. Include strong SEO metadata, responsive mobile navigation, accessible UI, polished animations and a professional visual design."
}
```

The response contains the workflow, durable run ID, workspace and `mode: "website"`.

The existing App Builder endpoint also supports explicit `mode: "website"` when an integration wants one common route.

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

The run creates an `APP_PREVIEW.json` file, starts the site only inside the isolated sandbox, obtains a browser-accessible preview URL through `sandbox_preview`, and records verification details in `PREVIEW_REPORT.md`.

The final application is packaged as `application.zip` with the platform's existing artifact integrity metadata.
