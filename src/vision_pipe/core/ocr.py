# src/vision_pipe/core/ocr.py
"""Native macOS OCR via Apple Vision Framework.

Fast, reliable text recognition — no VLM or API needed.
Supports Russian and English out of the box.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class OcrElement:
    text: str
    x: int
    y: int
    w: int
    h: int

    def center(self) -> tuple[int, int]:
        return self.x + self.w // 2, self.y + self.h // 2

    def to_dict(self) -> dict:
        return {"text": self.text, "x": self.x, "y": self.y, "w": self.w, "h": self.h}


def ocr_with_bounds(image_bytes: bytes, languages: list[str] | None = None, image_width: int | None = None, image_height: int | None = None) -> list[OcrElement]:
    import Vision
    from Foundation import NSData

    if languages is None:
        languages = ["ru", "en"]

    if image_width is None or image_height is None:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(image_bytes))
        image_width, image_height = img.size

    ns_data = NSData.dataWithBytes_length_(image_bytes, len(image_bytes))
    handler = Vision.VNImageRequestHandler.alloc().initWithData_options_(ns_data, None)
    request = Vision.VNRecognizeTextRequest.alloc().init()
    request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    request.setRecognitionLanguages_(languages)

    success, error = handler.performRequests_error_([request], None)
    if not success:
        return []

    results = request.results() or []
    elements: list[OcrElement] = []
    for obs in results:
        candidates = obs.topCandidates_(1)
        if not candidates:
            continue
        text = candidates[0].string()
        bbox = obs.boundingBox()
        # Apple Vision: origin bottom-left, normalized 0-1. Convert to top-left pixels.
        x = int(bbox.origin.x * image_width)
        y = int((1 - bbox.origin.y - bbox.size.height) * image_height)
        w = int(bbox.size.width * image_width)
        h = int(bbox.size.height * image_height)
        elements.append(OcrElement(text=text, x=x, y=y, w=w, h=h))
    return elements


def ocr_from_png(image_bytes: bytes, languages: list[str] | None = None) -> list[str]:
    """Run OCR on PNG image bytes using Apple Vision Framework.

    Returns list of recognized text blocks, top-to-bottom reading order.
    """
    elements = ocr_with_bounds(image_bytes, languages)
    return [e.text for e in elements]


def ocr_full_text(image_bytes: bytes, languages: list[str] | None = None) -> str:
    """Run OCR and return all text joined as a single string."""
    blocks = ocr_from_png(image_bytes, languages)
    return "\n".join(blocks)
