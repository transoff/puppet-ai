# tests/test_peripheral.py
import pytest
from puppet_ai.core.peripheral import PeripheralVision
from puppet_ai.types import FocusResult, RegionInfo, ScanResult


class MockProvider:
    def __init__(self, scan_result: ScanResult):
        self._scan_result = scan_result
        self.scan_calls: list[tuple] = []

    async def scan(self, image: bytes) -> ScanResult:
        self.scan_calls.append((len(image),))
        return self._scan_result

    async def focus(self, image: bytes, region: RegionInfo, context: str) -> FocusResult:
        return FocusResult(region_name=region.name, description="mock")


@pytest.fixture
def mock_provider(sample_scan_result):
    return MockProvider(sample_scan_result)


@pytest.fixture
def peripheral(mock_provider):
    return PeripheralVision(provider=mock_provider, resolution=(512, 512))


@pytest.mark.asyncio
async def test_scan_returns_result(peripheral, blank_image_bytes):
    result = await peripheral.scan(blank_image_bytes)
    assert result.summary == "Browser showing weather.com"
    assert len(result.regions) == 3


@pytest.mark.asyncio
async def test_scan_resizes_image(peripheral, blank_image_bytes, mock_provider):
    await peripheral.scan(blank_image_bytes)
    assert len(mock_provider.scan_calls) == 1
    sent_size = mock_provider.scan_calls[0][0]
    assert sent_size < len(blank_image_bytes)


@pytest.mark.asyncio
async def test_scan_with_custom_resolution(mock_provider, blank_image_bytes):
    pv = PeripheralVision(provider=mock_provider, resolution=(256, 256))
    await pv.scan(blank_image_bytes)
    assert len(mock_provider.scan_calls) == 1
