# tests/conftest.py
from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from puppet_ai.types import (
    Bounds,
    FocusResult,
    RegionInfo,
    ScanResult,
)


@pytest.fixture
def blank_image_bytes() -> bytes:
    """800x600 white PNG as bytes."""
    img = Image.new("RGB", (800, 600), color=(255, 255, 255))
    import io
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def changed_image_bytes() -> bytes:
    """800x600 PNG with a red rectangle in top-right corner."""
    img = Image.new("RGB", (800, 600), color=(255, 255, 255))
    pixels = np.array(img)
    pixels[0:100, 600:800] = [255, 0, 0]
    img = Image.fromarray(pixels)
    import io
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def sample_scan_result() -> ScanResult:
    return ScanResult(
        summary="Browser showing weather.com",
        regions=[
            RegionInfo(name="header", bounds=Bounds(x=0, y=0, w=800, h=60),
                       description="Navigation bar"),
            RegionInfo(name="content", bounds=Bounds(x=0, y=60, w=600, h=500),
                       description="Weather forecast"),
            RegionInfo(name="sidebar", bounds=Bounds(x=600, y=60, w=200, h=500),
                       description="Advertisements"),
        ],
    )


@pytest.fixture
def sample_focus_result() -> FocusResult:
    return FocusResult(
        region_name="content",
        description="Country A: 23°C, cloudy, wind 15 km/h NW, humidity 67%",
        extracted_data={"temperature": 23, "condition": "cloudy"},
    )
