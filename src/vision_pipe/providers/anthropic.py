from __future__ import annotations

import base64
import json
import os

from vision_pipe.types import Bounds, FocusResult, RegionInfo, ScanResult

SCAN_PROMPT = """Analyze this screenshot of a computer screen. Return a JSON object with:
- "summary": one-line description of what's visible
- "regions": array of objects with {"name": str, "bounds": {"x": int, "y": int, "w": int, "h": int}, "description": str}

Identify distinct UI regions (sidebar, chat list, message area, header, toolbar, etc).
Be precise about what each region contains.
Return ONLY valid JSON, no markdown fences."""

FOCUS_PROMPT = """You are looking at a cropped region of a computer screen.
Region name: {region_name}
Context: {context}

Describe EXACTLY what you see in detail:
- All text visible (read it precisely)
- UI elements (buttons, inputs, lists, avatars)
- Structure (what's a channel vs user vs message vs header)
- Any status indicators (online dots, badges, counts)

Return JSON with:
- "description": detailed description of everything visible
- "extracted_data": structured key-value data you can extract (usernames, channel names, messages, counts, etc)

Return ONLY valid JSON, no markdown fences."""


class AnthropicProvider:
    """Vision provider using Anthropic Claude API with custom base URL support."""

    def __init__(
        self,
        model: str = "claude-sonnet-4-6",
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.model = model
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._base_url = base_url or os.environ.get("ANTHROPIC_BASE_URL", "")

    async def _call(self, prompt: str, image: bytes) -> str:
        """Call Anthropic API via curl to handle custom endpoints (SSE streams)."""
        import asyncio

        image_b64 = base64.b64encode(image).decode()
        payload = json.dumps({
            "model": self.model,
            "max_tokens": 2048,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_b64,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        })

        base = self._base_url.rstrip("/") if self._base_url else "https://api.anthropic.com"
        url = f"{base}/v1/messages"

        proc = await asyncio.create_subprocess_exec(
            "curl", "-s", "-X", "POST", url,
            "-H", "Content-Type: application/json",
            "-H", f"x-api-key: {self._api_key}",
            "-H", "anthropic-version: 2023-06-01",
            "-d", payload,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
        raw = stdout.decode()

        # Handle SSE stream response (custom endpoints)
        if raw.startswith("event:"):
            text_parts = []
            for line in raw.split("\n"):
                if line.startswith("data:"):
                    try:
                        data = json.loads(line[5:].strip())
                        if data.get("type") == "content_block_delta":
                            delta = data.get("delta", {})
                            if delta.get("type") == "text_delta":
                                text_parts.append(delta.get("text", ""))
                    except json.JSONDecodeError:
                        pass
            return "".join(text_parts)

        # Handle standard JSON response
        try:
            data = json.loads(raw)
            if "content" in data and isinstance(data["content"], list):
                return data["content"][0].get("text", "")
            return raw
        except json.JSONDecodeError:
            return raw

    async def scan(self, image: bytes) -> ScanResult:
        text = await self._call(SCAN_PROMPT, image)
        # Strip markdown fences if present
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

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
            return ScanResult(summary=data.get("summary", ""), regions=regions)
        except (json.JSONDecodeError, KeyError):
            return ScanResult(summary=text[:200], regions=[])

    async def focus(
        self, image: bytes, region: RegionInfo, context: str
    ) -> FocusResult:
        prompt = FOCUS_PROMPT.format(context=context, region_name=region.name)
        text = await self._call(prompt, image)
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            data = json.loads(text)
            return FocusResult(
                region_name=region.name,
                description=data.get("description", text),
                extracted_data=data.get("extracted_data", {}),
            )
        except (json.JSONDecodeError, KeyError):
            return FocusResult(region_name=region.name, description=text)
