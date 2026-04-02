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


_retina_scale_cache: float | None = None


def _get_retina_scale() -> float:
    """Get Retina display scale factor. Cached after first call."""
    global _retina_scale_cache
    if _retina_scale_cache is not None:
        return _retina_scale_cache

    try:
        import Quartz
        main_display = Quartz.CGMainDisplayID()
        pixel_w = Quartz.CGDisplayPixelsWide(main_display)
        # Get logical width from display mode
        mode = Quartz.CGDisplayCopyDisplayMode(main_display)
        logical_w = Quartz.CGDisplayModeGetWidth(mode)
        _retina_scale_cache = pixel_w / logical_w if logical_w else 2.0
    except Exception:
        _retina_scale_cache = 2.0

    return _retina_scale_cache


def ocr_with_bounds(
    image_bytes: bytes,
    languages: list[str] | None = None,
    image_width: int | None = None,
    image_height: int | None = None,
    window_x: int = 0,
    window_y: int = 0,
) -> list[OcrElement]:
    """Run OCR and return elements with bounding boxes in ABSOLUTE screen coordinates.

    Coordinates are automatically:
    - Scaled for Retina displays (divided by scale factor)
    - Offset by window position (window_x, window_y)
    So they work directly with pyautogui click(x, y).
    """
    import Vision
    from Foundation import NSData

    if languages is None:
        languages = ["ru", "en"]

    if image_width is None or image_height is None:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(image_bytes))
        image_width, image_height = img.size

    # Get scale factor to convert from capture pixels to logical pixels
    scale = _get_retina_scale()

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
        # Apple Vision: origin bottom-left, normalized 0-1.
        # Convert to top-left, logical screen pixels (divided by Retina scale).
        # Add window offset for absolute screen coordinates.
        x = int((bbox.origin.x * image_width) / scale) + window_x
        y = int(((1 - bbox.origin.y - bbox.size.height) * image_height) / scale) + window_y
        w = int((bbox.size.width * image_width) / scale)
        h = int((bbox.size.height * image_height) / scale)
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
