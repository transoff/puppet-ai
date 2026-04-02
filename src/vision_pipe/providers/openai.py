from __future__ import annotations
import base64
import json
import os
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

class OpenAIProvider:
    def __init__(self, model: str = "gpt-4o-mini", api_key: str | None = None) -> None:
        self.model = model
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")

    async def _call(self, prompt: str, image: bytes) -> str:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=self._api_key)
        image_b64 = base64.b64encode(image).decode()
        response = await client.chat.completions.create(model=self.model, messages=[{"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}, {"type": "text", "text": prompt}]}], max_tokens=1024)
        return response.choices[0].message.content

    async def scan(self, image: bytes) -> ScanResult:
        text = await self._call(SCAN_PROMPT, image)
        data = json.loads(text)
        regions = [RegionInfo(name=r["name"], bounds=Bounds(**r["bounds"]), description=r.get("description", "")) for r in data.get("regions", [])]
        return ScanResult(summary=data["summary"], regions=regions)

    async def focus(self, image: bytes, region: RegionInfo, context: str) -> FocusResult:
        prompt = FOCUS_PROMPT_TEMPLATE.format(context=context, region_name=region.name)
        text = await self._call(prompt, image)
        data = json.loads(text)
        return FocusResult(region_name=region.name, description=data["description"], extracted_data=data.get("extracted_data", {}))
