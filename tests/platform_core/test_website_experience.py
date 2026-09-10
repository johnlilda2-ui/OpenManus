import base64
import io

from PIL import Image

from platform_core.visual_diff import average_hash, hash_similarity
from platform_core.website_iteration import build_website_section_iteration_steps
from platform_core.website_manifest import extract_visual_score, extract_website_manifests


def _png_base64(value: int) -> str:
    image = Image.new("RGB", (64, 64), (value, value, value))
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    return base64.b64encode(stream.getvalue()).decode()


def test_website_manifests_are_extracted_from_builder_result():
    text = '''
DESIGN_SYSTEM_JSON:
```json
{"tokens":{"colors":{"primary":"#123456"}},"components":{"button":{"variants":["primary"]}}}
```
SECTION_MANIFEST_JSON:
```json
[{"id":"home.hero","page":"/","name":"Hero","anchor":"hero","selector":"#home.hero","description":"Main hero","sort_order":0}]
```
ASSET_MANIFEST_JSON:
```json
[{"id":"hero.image","kind":"image","name":"Hero image","path_or_url":"/assets/hero.webp","alt_text":"Hero scene","usage":"hero"}]
```
'''
    design, sections, assets = extract_website_manifests([text])
    assert design["tokens"]["colors"]["primary"] == "#123456"
    assert sections[0]["section_id"] == "home.hero"
    assert assets[0]["id"] == "hero.image"


def test_visual_hash_similarity_is_deterministic():
    first = average_hash(_png_base64(50))
    second = average_hash(_png_base64(50))
    different = average_hash(_png_base64(200))
    assert first == second
    assert hash_similarity(first, second) == 100.0
    assert 0.0 <= hash_similarity(first, different) <= 100.0


def test_visual_score_marker_is_parsed():
    result = '{"visual_hash":"ffff","reference_hash":"ff00","visual_diff_score":93.5,"url":"https://preview.example"}'
    score = extract_visual_score([result])
    assert score["score"] == 93.5
    assert score["current_hash"] == "ffff"
    assert score["baseline_hash"] == "ff00"


def test_section_iteration_workflow_targets_one_section():
    steps = build_website_section_iteration_steps("project-1", "home.hero", "Make the hero clearer and more premium")
    assert len(steps) == 6
    assert all("home.hero" in step["prompt"] for step in steps)
    assert steps[1]["role"] == "designer"
    assert steps[3]["browser_required"] is True
    assert steps[5]["browser_required"] is True
