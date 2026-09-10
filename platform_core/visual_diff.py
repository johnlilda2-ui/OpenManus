from __future__ import annotations

import base64
import hashlib
import io

from PIL import Image


def _decode_image(base64_image: str) -> Image.Image:
    payload = base64_image.split(",", 1)[1] if base64_image.startswith("data:") else base64_image
    raw = base64.b64decode(payload, validate=True)
    with Image.open(io.BytesIO(raw)) as image:
        return image.convert("L").copy()


def average_hash(base64_image: str, size: int = 16) -> str:
    image = _decode_image(base64_image).resize((size, size))
    pixels = list(image.getdata())
    average = sum(pixels) / len(pixels)
    bits = "".join("1" if value >= average else "0" for value in pixels)
    return f"{int(bits, 2):0{len(bits) // 4}x}"


def image_sha256(base64_image: str) -> str:
    payload = base64_image.split(",", 1)[1] if base64_image.startswith("data:") else base64_image
    raw = base64.b64decode(payload, validate=True)
    return hashlib.sha256(raw).hexdigest()


def hash_similarity(reference_hash: str, current_hash: str) -> float:
    if not reference_hash or not current_hash or len(reference_hash) != len(current_hash):
        raise ValueError("Visual hashes must be non-empty and have equal length")
    reference = int(reference_hash, 16)
    current = int(current_hash, 16)
    distance = (reference ^ current).bit_count()
    total_bits = len(reference_hash) * 4
    return round(max(0.0, 1.0 - (distance / total_bits)) * 100.0, 2)
