from __future__ import annotations
import base64, json
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

class SamplingProvider:
    """Uses MCP Sampling to request inference from the agent's own model."""
    def __init__(self, hint: str | None = None) -> None:
        self._hint = hint
        self._sampling_fn = None

    def set_sampling_fn(self, fn) -> None:
        self._sampling_fn = fn

    async def _call(self, prompt: str, image_b64: str) -> str:
        if self._sampling_fn is None:
            raise RuntimeError("SamplingProvider requires MCP sampling. Set sampling function via set_sampling_fn().")
        return await self._sampling_fn(prompt=prompt, image_b64=image_b64, hint=self._hint)

    async def scan(self, image: bytes) -> ScanResult:
        image_b64 = base64.b64encode(image).decode()
        text = await self._call(SCAN_PROMPT, image_b64)
        data = json.loads(text)
        regions = [RegionInfo(name=r["name"], bounds=Bounds(**r["bounds"]), description=r.get("description", "")) for r in data.get("regions", [])]
        return ScanResult(summary=data["summary"], regions=regions)

    async def focus(self, image: bytes, region: RegionInfo, context: str) -> FocusResult:
        image_b64 = base64.b64encode(image).decode()
        prompt = FOCUS_PROMPT_TEMPLATE.format(context=context, region_name=region.name)
        text = await self._call(prompt, image_b64)
        data = json.loads(text)
        return FocusResult(region_name=region.name, description=data["description"], extracted_data=data.get("extracted_data", {}))
