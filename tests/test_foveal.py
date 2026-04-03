# tests/test_foveal.py
import pytest
from PIL import Image
import io
import numpy as np
from puppet_ai.core.foveal import FovealFocus
from puppet_ai.types import Bounds, FocusResult, RegionInfo, ScanResult


class MockFocusProvider:
    def __init__(self):
        self.focus_calls: list[dict] = []

    async def scan(self, image: bytes) -> ScanResult:
        return ScanResult(summary="mock", regions=[])

    async def focus(self, image: bytes, region: RegionInfo, context: str) -> FocusResult:
        img = Image.open(io.BytesIO(image))
        self.focus_calls.append({"size": img.size, "region": region.name, "context": context})
        return FocusResult(region_name=region.name, description=f"Detailed view of {region.name}", extracted_data={"test": True})


@pytest.fixture
def mock_provider():
    return MockFocusProvider()


@pytest.fixture
def foveal(mock_provider):
    return FovealFocus(provider=mock_provider)


@pytest.fixture
def large_image_bytes():
    img = np.full((800, 1200, 3), 200, dtype=np.uint8)
    img[0:100, 0:1200] = [50, 50, 200]
    img[100:700, 0:800] = [50, 200, 50]
    img[100:700, 800:1200] = [200, 50, 50]
    pil_img = Image.fromarray(img)
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_focus_crops_region(foveal, large_image_bytes, mock_provider):
    region = RegionInfo(name="content", bounds=Bounds(x=0, y=100, w=800, h=600))
    result = await foveal.focus(large_image_bytes, region, "Find data")
    assert result.region_name == "content"
    assert len(mock_provider.focus_calls) == 1
    assert mock_provider.focus_calls[0]["size"] == (800, 600)


@pytest.mark.asyncio
async def test_focus_passes_context(foveal, large_image_bytes, mock_provider):
    region = RegionInfo(name="header", bounds=Bounds(x=0, y=0, w=1200, h=100))
    await foveal.focus(large_image_bytes, region, "Check navigation")
    assert mock_provider.focus_calls[0]["context"] == "Check navigation"


@pytest.mark.asyncio
async def test_focus_returns_extracted_data(foveal, large_image_bytes):
    region = RegionInfo(name="content", bounds=Bounds(x=0, y=100, w=800, h=600))
    result = await foveal.focus(large_image_bytes, region, "test")
    assert result.extracted_data == {"test": True}
