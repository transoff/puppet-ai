# src/puppet_ai/providers/ollama.py
from __future__ import annotations

import asyncio
import base64
import json
import subprocess
import sys

from puppet_ai.types import Bounds, FocusResult, RegionInfo, ScanResult

SCAN_PROMPT = """<image>
Describe what you see on this computer screen. List the main areas/regions visible (header, content, sidebar, etc), what application is open, and any key text or data visible. Be specific and concise."""

FOCUS_PROMPT_TEMPLATE = """<image>
Analyze this cropped screen region in detail.
Context: {context}
Region: {region_name}
Describe all text, data, and visual elements you can see. Be specific."""


class OllamaProvider:
    """Vision provider using Ollama local models.

    Uses subprocess+curl instead of httpx to avoid proxy issues (e.g. Throne VPN).
    Moondream requires <image> prefix in prompts for vision to work via API.
    """

    def __init__(
        self,
        model: str = "moondream",
        base_url: str = "http://localhost:11434",
    ) -> None:
        self.model = model
        self.base_url = base_url

    async def _call(self, prompt: str, image_b64: str) -> str:
        """Call Ollama API via curl (bypasses proxy issues with httpx)."""
        payload = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "images": [image_b64],
            "stream": False,
        })

        proc = await asyncio.create_subprocess_exec(
            "curl", "-s", "-X", "POST",
            f"{self.base_url}/api/generate",
            "-H", "Content-Type: application/json",
            "-d", payload,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

        if proc.returncode != 0:
            raise RuntimeError(f"Ollama call failed: {stderr.decode()}")

        data = json.loads(stdout.decode())
        response_text = data.get("response", "")

        if not response_text.strip():
            raise RuntimeError(f"Ollama returned empty response for model {self.model}")

        return response_text

    async def scan(self, image: bytes) -> ScanResult:
        image_b64 = base64.b64encode(image).decode()
        text = await self._call(SCAN_PROMPT, image_b64)

        # Try to parse as JSON first, fall back to plain text
        try:
            data = json.loads(text)
            regions = [
                RegionInfo(
                    name=r["name"],
                    bounds=Bounds(**r["bounds"]),
                    description=r.get("description", ""),
                )
                for r in data.get("regions", [])
            ]
            return ScanResult(summary=data.get("summary", text), regions=regions)
        except (json.JSONDecodeError, KeyError):
            # Moondream often returns plain text, not JSON
            return ScanResult(summary=text.strip(), regions=[])

    async def focus(
        self, image: bytes, region: RegionInfo, context: str
    ) -> FocusResult:
        image_b64 = base64.b64encode(image).decode()
        prompt = FOCUS_PROMPT_TEMPLATE.format(context=context, region_name=region.name)
        text = await self._call(prompt, image_b64)

        try:
            data = json.loads(text)
            return FocusResult(
                region_name=region.name,
                description=data.get("description", text),
                extracted_data=data.get("extracted_data", {}),
            )
        except (json.JSONDecodeError, KeyError):
            return FocusResult(
                region_name=region.name,
                description=text.strip(),
            )

    async def close(self) -> None:
        pass
