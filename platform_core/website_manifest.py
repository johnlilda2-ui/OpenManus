from __future__ import annotations

import json
import re


def extract_json_marker(text: str, marker: str) -> dict | list | None:
    pattern = rf"{re.escape(marker)}\s*:\s*```json\s*(.*?)```"
    match = re.search(pattern, text or "", flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1).strip())
    except json.JSONDecodeError:
        return None


def extract_website_manifests(step_results: list[str]) -> tuple[dict, list[dict], list[dict]]:
    design_system: dict = {}
    sections: list[dict] = []
    assets: list[dict] = []
    for result in step_results:
        parsed_design = extract_json_marker(result, "DESIGN_SYSTEM_JSON")
        parsed_sections = extract_json_marker(result, "SECTION_MANIFEST_JSON")
        parsed_assets = extract_json_marker(result, "ASSET_MANIFEST_JSON")
        if isinstance(parsed_design, dict):
            design_system = parsed_design
        if isinstance(parsed_sections, list):
            sections = [item for item in parsed_sections if isinstance(item, dict)]
        elif isinstance(parsed_sections, dict) and isinstance(parsed_sections.get("sections"), list):
            sections = [item for item in parsed_sections["sections"] if isinstance(item, dict)]
        if isinstance(parsed_assets, list):
            assets = [item for item in parsed_assets if isinstance(item, dict)]
        elif isinstance(parsed_assets, dict) and isinstance(parsed_assets.get("assets"), list):
            assets = [item for item in parsed_assets["assets"] if isinstance(item, dict)]
    sections = sorted(
        sections,
        key=lambda item: (str(item.get("page", "/")), int(item.get("sort_order", 0)), str(item.get("id", ""))),
    )
    normalized_sections = [
        {
            "section_id": str(item.get("id") or item.get("section_id") or "").strip(),
            "page": str(item.get("page") or "/"),
            "name": str(item.get("name") or item.get("title") or "Untitled section"),
            "anchor": item.get("anchor"),
            "selector": item.get("selector"),
            "description": item.get("description"),
            "sort_order": int(item.get("sort_order", index)),
        }
        for index, item in enumerate(sections)
        if str(item.get("id") or item.get("section_id") or "").strip()
    ]
    normalized_assets = [
        {
            "id": str(item.get("id") or item.get("asset_id") or "").strip(),
            "kind": str(item.get("kind") or "image"),
            "name": str(item.get("name") or item.get("id") or "Asset"),
            "path_or_url": item.get("path_or_url") or item.get("path") or item.get("source_url"),
            "alt_text": item.get("alt_text") or item.get("alt"),
            "usage": item.get("usage"),
            "width": item.get("width"),
            "height": item.get("height"),
        }
        for item in assets
        if str(item.get("id") or item.get("asset_id") or "").strip()
    ]
    return design_system, normalized_sections, normalized_assets


def extract_visual_score(step_results: list[str]) -> dict[str, object | None]:
    for result in reversed(step_results):
        matches = re.findall(r"\{\s*\"visual_hash\".*?\}", result or "", flags=re.DOTALL)
        for candidate in reversed(matches):
            try:
                data = json.loads(candidate)
                return {
                    "score": float(data["visual_diff_score"]) if data.get("visual_diff_score") is not None else None,
                    "baseline_hash": data.get("reference_hash"),
                    "current_hash": data.get("visual_hash"),
                    "url": data.get("url"),
                }
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
        match = re.search(r"visual_diff_score\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)", result or "", flags=re.IGNORECASE)
        if match:
            return {"score": float(match.group(1)), "baseline_hash": None, "current_hash": None, "url": None}
    return {"score": None, "baseline_hash": None, "current_hash": None, "url": None}
