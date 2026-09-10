from platform_core.app_builder import build_app_builder_steps, project_workspace
from platform_core.model_router import resolve_profile
from platform_core.schemas import AppBuilderCreate
from platform_core.website_builder import build_website_builder_steps
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


def test_website_builder_has_design_seo_and_browser_phases():
    steps = build_website_builder_steps(
        "site-456",
        "Build a modern logistics company website with Home, Services, Fleet and Contact",
    )
    assert len(steps) == 10
    names = [step["name"] for step in steps]
    assert names[0] == "Website strategy and information architecture"
    assert names[2] == "Visual frontend implementation"
    assert names[3] == "SEO, accessibility and performance hardening"
    assert names[5] == "Run and preview"
    assert steps[6]["role"] == "tester"
    assert steps[7]["browser_required"] is True
    assert steps[8]["role"] == "fixer"
    assert steps[9]["browser_required"] is False
    assert "sitemap.xml" in steps[3]["prompt"]
    assert "QA_STATUS: FAIL" in steps[7]["prompt"]
    assert "site-456" in steps[0]["prompt"]


def test_website_builder_reuses_autonomous_preview_repair_loop():
    steps = build_website_builder_steps("site-789", "Build a responsive business website")
    assert "sandbox_preview" in steps[5]["prompt"]
    assert "QA_FAILURES.md" in steps[8]["prompt"]
    assert "QA_STATUS: PASS" in steps[9]["prompt"]


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
