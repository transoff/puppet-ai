# tests/test_providers/test_ollama.py
import json
import httpx
import pytest
from vision_pipe.providers.ollama import OllamaProvider
from vision_pipe.types import Bounds, RegionInfo


class FakeTransport(httpx.AsyncBaseTransport):
    def __init__(self, response_body: str):
        self._body = response_body

    async def handle_async_request(self, request):
        return httpx.Response(200, json={"response": self._body})


@pytest.fixture
def scan_response():
    return json.dumps({
        "summary": "Browser showing weather.com",
        "regions": [
            {"name": "header", "bounds": {"x": 0, "y": 0, "w": 800, "h": 60}, "description": "Navigation"},
            {"name": "content", "bounds": {"x": 0, "y": 60, "w": 600, "h": 500}, "description": "Weather data"},
        ],
    })


@pytest.fixture
def focus_response():
    return json.dumps({
        "description": "Country A: 23°C, cloudy",
        "extracted_data": {"temperature": 23},
    })


@pytest.mark.asyncio
async def test_scan_parses_response(blank_image_bytes, scan_response):
    transport = FakeTransport(scan_response)
    client = httpx.AsyncClient(transport=transport)
    provider = OllamaProvider(model="moondream2", base_url="http://localhost:11434")
    provider._client = client
    result = await provider.scan(blank_image_bytes)
    assert result.summary == "Browser showing weather.com"
    assert len(result.regions) == 2
    assert result.regions[0].name == "header"


@pytest.mark.asyncio
async def test_focus_parses_response(blank_image_bytes, focus_response):
    transport = FakeTransport(focus_response)
    client = httpx.AsyncClient(transport=transport)
    provider = OllamaProvider(model="moondream2", base_url="http://localhost:11434")
    provider._client = client
    region = RegionInfo(name="content", bounds=Bounds(x=0, y=60, w=600, h=500))
    result = await provider.focus(blank_image_bytes, region, "Find temperature")
    assert result.region_name == "content"
    assert "23°C" in result.description
