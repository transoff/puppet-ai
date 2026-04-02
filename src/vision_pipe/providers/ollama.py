# src/vision_pipe/providers/ollama.py
from __future__ import annotations
import base64
import json
import httpx
from vision_pipe.types import Bounds, FocusResult, RegionInfo, ScanResult

SCAN_PROMPT = """Analyze this screenshot. Return JSON with:
- "summary": one-line description of what's on screen
- "regions": array of {"name": str, "bounds": {"x": int, "y": int, "w": int, "h": int}, "description": str}
Identify distinct visual regions. Return ONLY valid JSON."""

FOCUS_PROMPT_TEMPLATE = """Analyze this cropped screen region in detail.
Context: {context}
Region: {region_name}
Return JSON with:
- "description": detailed description
- "extracted_data": key-value pairs of structured data
Return ONLY valid JSON."""


class OllamaProvider:
    def __init__(self, model: str = "moondream2", base_url: str = "http://localhost:11434") -> None:
        self.model = model
        self.base_url = base_url
        self._client = httpx.AsyncClient(timeout=30.0)

    async def scan(self, image: bytes) -> ScanResult:
        image_b64 = base64.b64encode(image).decode()
        response = await self._client.post(
            f"{self.base_url}/api/generate",
            json={"model": self.model, "prompt": SCAN_PROMPT, "images": [image_b64], "stream": False},
        )
        response.raise_for_status()
        text = response.json()["response"]
        data = json.loads(text)
        regions = [
            RegionInfo(
                name=r["name"],
                bounds=Bounds(**r["bounds"]),
                description=r.get("description", ""),
            )
            for r in data.get("regions", [])
        ]
        return ScanResult(summary=data["summary"], regions=regions)

    async def focus(self, image: bytes, region: RegionInfo, context: str) -> FocusResult:
        image_b64 = base64.b64encode(image).decode()
        prompt = FOCUS_PROMPT_TEMPLATE.format(context=context, region_name=region.name)
        response = await self._client.post(
            f"{self.base_url}/api/generate",
            json={"model": self.model, "prompt": prompt, "images": [image_b64], "stream": False},
        )
        response.raise_for_status()
        text = response.json()["response"]
        data = json.loads(text)
        return FocusResult(
            region_name=region.name,
            description=data["description"],
            extracted_data=data.get("extracted_data", {}),
        )

    async def close(self) -> None:
        await self._client.aclose()
