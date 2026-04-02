# src/vision_pipe/core/ocr.py
"""Native macOS OCR via Apple Vision Framework.

Fast, reliable text recognition — no VLM or API needed.
Supports Russian and English out of the box.
"""
from __future__ import annotations


def ocr_from_png(image_bytes: bytes, languages: list[str] | None = None) -> list[str]:
    """Run OCR on PNG image bytes using Apple Vision Framework.

    Returns list of recognized text blocks, top-to-bottom reading order.
    """
    import Vision
    from Foundation import NSData

    if languages is None:
        languages = ["ru", "en"]

    ns_data = NSData.dataWithBytes_length_(image_bytes, len(image_bytes))
    handler = Vision.VNImageRequestHandler.alloc().initWithData_options_(ns_data, None)
    request = Vision.VNRecognizeTextRequest.alloc().init()
    request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    request.setRecognitionLanguages_(languages)

    success, error = handler.performRequests_error_([request], None)
    if not success:
        return []

    results = request.results() or []
    texts = []
    for obs in results:
        candidates = obs.topCandidates_(1)
        if candidates:
            texts.append(candidates[0].string())

    return texts


def ocr_full_text(image_bytes: bytes, languages: list[str] | None = None) -> str:
    """Run OCR and return all text joined as a single string."""
    blocks = ocr_from_png(image_bytes, languages)
    return "\n".join(blocks)
