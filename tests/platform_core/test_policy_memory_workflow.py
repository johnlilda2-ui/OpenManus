def test_policy_defaults_are_conservative():
    from platform_core.policy import PolicyDenied, ToolPolicy

    policy = ToolPolicy.defaults()
    policy.authorize("web_search")
    policy.authorize("browser_exec")

    try:
        policy.authorize("bash")
    except PolicyDenied as exc:
        assert exc.tool_name == "bash"
    else:
        raise AssertionError("bash must be denied by the default project policy")


def test_workflow_template_rendering():
    from platform_core.workflows import normalize_steps, render_step_prompt

    steps = normalize_steps(
        [
            {"name": "Research", "prompt": "Research {{input}}"},
            {"name": "Summarize", "prompt": "Summarize {{previous_output}} for {{input}}"},
        ]
    )
    assert steps[0]["name"] == "Research"
    rendered = render_step_prompt(steps[1]["prompt"], input_text="AI agents", previous_output="Useful findings", step_index=1)
    assert rendered == "Summarize Useful findings for AI agents"


def test_memory_context_keeps_request():
    from platform_core.memory import build_context

    rendered = build_context(prompt="What should I do next?", recent_messages=[], memories=[], documents=[])
    assert rendered == "What should I do next?"
