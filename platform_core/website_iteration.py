from __future__ import annotations


def build_website_section_iteration_steps(project_id: str, section_id: str, instruction: str) -> list[dict]:
    workspace = f"workspace/projects/{project_id}"
    shared = f"""
You are iterating one section of an existing production website in {workspace}.
Target section ID: {section_id}
User requested change: {instruction}
Read SECTION_MANIFEST.json and DESIGN_SYSTEM.json first. Preserve all unrelated pages and sections.
Do not rewrite the entire website. Keep stable IDs, design tokens, accessibility, SEO and existing behavior intact.
""".strip()
    return [
        {
            "name": "Inspect target section",
            "role": "planner",
            "prompt": f"""{shared}

Locate the exact section in the current project using SECTION_MANIFEST.json and the codebase.
Identify the smallest set of files/components/styles required to make the requested change.
Create {workspace}/SECTION_ITERATION_PLAN.md with the target files, affected selectors/components,
acceptance criteria, and explicit out-of-scope areas.""",
            "max_attempts": 1,
            "browser_required": False,
        },
        {
            "name": "Regenerate target section",
            "role": "designer",
            "prompt": f"""{shared}

Read SECTION_ITERATION_PLAN.md. Implement only the requested changes to section `{section_id}`.
Use the existing design system. Keep the same section ID and preserve its page semantics, responsive
behavior, links, forms and accessibility unless the request explicitly changes them. Do not touch unrelated sections.""",
            "max_attempts": 2,
            "browser_required": False,
        },
        {
            "name": "Run and preview iteration",
            "role": "tester",
            "prompt": f"""{shared}

Read APP_PREVIEW.json. Restart or reuse the preview only inside the isolated sandbox. Health-check the
site and use sandbox_preview to obtain the browser-accessible URL. Confirm the target section is present
on the expected route. Write {workspace}/ITERATION_PREVIEW_REPORT.md with the URL, route, and health result.""",
            "max_attempts": 2,
            "browser_required": False,
        },
        {
            "name": "Targeted browser verification",
            "role": "reviewer",
            "prompt": f"""{shared}

Use sandbox_browser against the preview URL from ITERATION_PREVIEW_REPORT.md. Navigate directly to the
page containing `{section_id}` and verify the requested change, responsive behavior, links/CTAs, visual
hierarchy and accessibility basics. Also confirm at least one unrelated section remains unchanged.
Call sandbox_browser with action=snapshot and record its `visual_hash` in {workspace}/ITERATION_BASELINE_OR_CURRENT.json.
Write {workspace}/ITERATION_QA.md and end with exactly ITERATION_STATUS: PASS or ITERATION_STATUS: FAIL.""",
            "max_attempts": 2,
            "browser_required": True,
        },
        {
            "name": "Repair target section",
            "role": "fixer",
            "prompt": f"""{shared}

Read ITERATION_QA.md. If ITERATION_STATUS: PASS, make no further functional changes.
If FAIL, fix only the reproducible target-section issues in the isolated workspace. Preserve unrelated
sections and the design system. Rerun focused checks and update {workspace}/ITERATION_REPAIR.md with what changed.""",
            "max_attempts": 2,
            "browser_required": False,
        },
        {
            "name": "Final section re-verification",
            "role": "reviewer",
            "prompt": f"""{shared}

Re-open the target section in the running preview and verify the requested change after repair.
Call sandbox_browser action=snapshot with reference_hash from ITERATION_BASELINE_OR_CURRENT.json when available.
Record visual_diff_score, current visual_hash, and verified URL in {workspace}/ITERATION_VISUAL_DIFF.json.
Write {workspace}/ITERATION_FINAL.md with the final status. End with ITERATION_STATUS: PASS only when the
requested change was actually verified; otherwise ITERATION_STATUS: FAIL.""",
            "max_attempts": 2,
            "browser_required": True,
        },
    ]
