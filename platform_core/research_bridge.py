from __future__ import annotations


def apply_website_research_context(
    steps: list[dict],
    *,
    synthesis: str | None,
    references: list[dict] | None = None,
) -> list[dict]:
    """Inject a compact research brief into Website Builder without rerunning research."""
    synthesis = (synthesis or "").strip()
    refs = references or []
    if not synthesis and not refs:
        return steps

    lines = [
        "\n\nRESEARCH BRIEF (already completed; do not rerun web research):",
        "Use this evidence as design/UX guidance. Do not copy proprietary text, images, logos, trademarks, exact layouts, or branding.",
    ]
    if synthesis:
        lines.append(f"Planner synthesis:\n{synthesis[:10000]}")
    if refs:
        lines.append("Validated research references:")
        for index, ref in enumerate(refs[:2], 1):
            title = str(ref.get("title") or ref.get("name") or "Untitled").strip()[:300]
            url = str(ref.get("url") or "").strip()[:1000]
            description = str(ref.get("description") or "").strip()[:700]
            lines.append(f"Reference {index}: {title} | {url}\n{description}")
    context = "\n".join(lines)

    enriched = []
    for step in steps:
        item = dict(step)
        role = str(item.get("role") or "").lower()
        # The compact brief is useful to planning/design/build/review roles, but the
        # final context is intentionally bounded so we do not inflate every prompt.
        if role in {"planner", "designer", "builder", "tester", "fixer", "reviewer"}:
            item["prompt"] = f"{item['prompt']}\n{context}"
        enriched.append(item)
    return enriched
