from __future__ import annotations
import pytest
from PIL import Image, ImageDraw
import io
from vision_pipe.core.ocr import ocr_with_bounds, OcrElement


@pytest.fixture
def image_with_text() -> bytes:
    img = Image.new("RGB", (400, 200), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((50, 80), "Hello World", fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_ocr_with_bounds_returns_elements(image_with_text):
    elements = ocr_with_bounds(image_with_text)
    assert len(elements) > 0
    assert all(isinstance(e, OcrElement) for e in elements)


def test_ocr_element_has_text_and_coords(image_with_text):
    elements = ocr_with_bounds(image_with_text)
    for elem in elements:
        assert isinstance(elem.text, str) and len(elem.text) > 0
        assert isinstance(elem.x, int) and isinstance(elem.y, int)
        assert isinstance(elem.w, int) and elem.w > 0
        assert isinstance(elem.h, int) and elem.h > 0


def test_ocr_element_center(image_with_text):
    elements = ocr_with_bounds(image_with_text)
    if elements:
        e = elements[0]
        cx, cy = e.center()
        assert cx == e.x + e.w // 2
        assert cy == e.y + e.h // 2


def test_ocr_with_bounds_empty_image():
    img = Image.new("RGB", (100, 100), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    elements = ocr_with_bounds(buf.getvalue())
    assert elements == []


def test_ocr_element_serialization(image_with_text):
    elements = ocr_with_bounds(image_with_text)
    if elements:
        d = elements[0].to_dict()
        assert "text" in d and "x" in d and "y" in d and "w" in d and "h" in d
