from platform_core.app_builder import build_app_builder_steps, project_workspace
from platform_core.model_router import resolve_profile
from platform_core.workflows import normalize_steps


def test_app_builder_has_expected_release_phases():
    steps = build_app_builder_steps("project-123", "Build a task dashboard with authentication and a polished responsive UI")
    assert len(steps) == 8
    assert steps[0]["role"] == "planner"
    assert steps[1]["role"] == "builder"
    assert steps[2]["role"] == "designer"
    assert steps[4]["max_attempts"] == 2
    assert steps[5]["max_attempts"] == 3
    assert steps[6]["browser_required"] is True
    assert "project-123" in steps[0]["prompt"]


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
