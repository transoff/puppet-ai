"""Draw numbered element IDs on screenshots for click-by-number."""
from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont
import io


def draw_element_ids(
    image_bytes: bytes,
    elements: list[dict],
    max_elements: int = 50,
) -> tuple[bytes, list[dict]]:
    """Draw numbered labels on screenshot at element positions.

    Returns: (annotated_image_bytes, indexed_elements with "id" field added)
    """
    pil = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    draw = ImageDraw.Draw(pil)

    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
    except Exception:
        font = ImageFont.load_default()

    indexed = []
    for i, el in enumerate(elements[:max_elements]):
        x, y, w, h = el.get("x", 0), el.get("y", 0), el.get("w", 0), el.get("h", 0)
        if w < 3 or h < 3:
            continue

        label = str(i)
        draw.rectangle([x, y, x + w, y + h], outline="red", width=1)
        bbox = font.getbbox(label)
        lw, lh = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.rectangle([x - 1, y - lh - 3, x + lw + 3, y - 1], fill="red")
        draw.text((x + 1, y - lh - 2), label, fill="white", font=font)

        el_copy = dict(el)
        el_copy["id"] = i
        indexed.append(el_copy)

    buf = io.BytesIO()
    pil.save(buf, format="JPEG", quality=80)
    return buf.getvalue(), indexed
