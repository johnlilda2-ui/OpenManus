from platform_core.app_builder import build_app_builder_steps, project_workspace
from platform_core.model_router import resolve_profile
from platform_core.schemas import AppBuilderCreate
from platform_core.website_builder import build_website_builder_steps
from platform_core.website_manifest import extract_website_research
from platform_core.website_iteration import build_website_section_iteration_steps
from platform_core.workflows import normalize_steps


def test_app_builder_has_autonomous_release_phases():
    steps = build_app_builder_steps(
        "project-123",
        "Build a task dashboard with authentication and a polished responsive UI",
    )
    assert len(steps) == 10
    assert steps[0]["role"] == "planner"
    assert steps[1]["role"] == "builder"
    assert steps[2]["role"] == "designer"
    assert steps[3]["name"] == "Integration and preview configuration"
    assert steps[4]["name"] == "Run and preview"
    assert steps[5]["name"] == "Automated test and repair"
    assert steps[6]["browser_required"] is True
    assert steps[7]["role"] == "fixer"
    assert steps[8]["browser_required"] is True
    assert steps[9]["name"] == "Final security and release review"
    assert "sandbox_preview" in steps[4]["prompt"]
    assert "QA_STATUS: FAIL" in steps[6]["prompt"]
    assert "QA_STATUS: PASS" in steps[8]["prompt"]
    assert "project-123" in steps[0]["prompt"]


def test_website_builder_has_research_design_assets_seo_and_browser_phases():
    steps = build_website_builder_steps(
        "site-456",
        "Build a modern marketplace for independent artisans with discovery, search, filters, listings and seller profiles",
    )
    assert len(steps) == 14
    names = [step["name"] for step in steps]
    assert names[0] == "Reference research and design inspiration"
    assert names[1] == "Website strategy and information architecture"
    assert names[2] == "Design system and page manifest"
    assert names[3] == "Content and page system"
    assert names[4] == "Visual asset creation and sourcing"
    assert names[5] == "Visual frontend implementation"
    assert names[6] == "SEO, accessibility and performance hardening"
    assert names[7] == "Integration and preview configuration"
    assert names[8] == "Run and preview"
    assert names[9] == "Automated website test and repair"
    assert names[10] == "Browser visual and UX verification"
    assert names[11] == "Autonomous website repair"
    assert names[12] == "Browser re-verification and visual diff"
    assert names[13] == "Final website release review"
    assert steps[0]["role"] == "planner"
    assert "web_search" in steps[0]["prompt"]
    assert "exactly 1 or 2" in steps[0]["prompt"]
    assert "do not copy" in steps[0]["prompt"].lower()
    assert "DESIGN_SYSTEM.json" in steps[2]["prompt"]
    assert "ASSET_MANIFEST.json" in steps[2]["prompt"]
    assert "original local SVG" in steps[4]["prompt"]
    assert "sitemap.xml" in steps[6]["prompt"]
    assert "sandbox_preview" in steps[8]["prompt"]
    assert steps[10]["browser_required"] is True
    assert "VISUAL_BASELINE.json" in steps[10]["prompt"]
    assert steps[12]["browser_required"] is True
    assert "visual_diff_score" in steps[12]["prompt"]
    assert "site-456" in steps[0]["prompt"]


def test_website_builder_iteration_preserves_research_and_target_scope():
    steps = build_website_section_iteration_steps(
        "site-789", "home.featured-listings", "Make the cards more premium and improve mobile spacing"
    )
    assert len(steps) == 6
    assert "WEBSITE_RESEARCH.md" in steps[0]["prompt"]
    assert "do not copy" in steps[0]["prompt"].lower()
    assert "home.featured-listings" in steps[1]["prompt"]
    assert "unrelated" in steps[3]["prompt"].lower()
    assert "visual_diff_score" in steps[5]["prompt"]


def test_website_research_parser_limits_to_two_references():
    results = [
        "WEBSITE_RESEARCH_JSON:\n```json\n{\"website_type\":\"marketplace\",\"references\":[{\"name\":\"A\",\"url\":\"https://a.example\"},{\"name\":\"B\",\"url\":\"https://b.example\"},{\"name\":\"C\",\"url\":\"https://c.example\"}]}\n```"
    ]
    research = extract_website_research(results)
    assert research["website_type"] == "marketplace"
    assert len(research["references"]) == 2
    assert research["references"][0]["name"] == "A"


def test_workflow_normalization_preserves_builder_metadata():
    normalized = normalize_steps(
        [
            {
                "name": "UI",
                "prompt": "Build the UI",
                "role": "designer",
                "model_profile": "gemini_flash",
                "max_attempts": 2,
                "browser_required": True,
            }
        ]
    )
    assert normalized[0]["role"] == "designer"
    assert normalized[0]["model_profile"] == "gemini_flash"
    assert normalized[0]["max_attempts"] == 2
    assert normalized[0]["browser_required"] is True


def test_model_router_falls_back_to_default_profile():
    profile = resolve_profile("designer", "definitely-not-configured")
    assert profile.role == "designer"
    assert profile.config_name == "default"


def test_project_workspace_is_deterministic():
    assert project_workspace("abc") == "workspace/projects/abc"


def test_app_builder_request_supports_explicit_website_mode():
    payload = AppBuilderCreate(
        requirements="Build a polished business website with SEO and contact form",
        mode="website",
    )
    assert payload.mode == "website"
