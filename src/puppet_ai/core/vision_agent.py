# src/puppet_ai/core/vision_agent.py
"""AI vision agent — analyzes screenshots via fast model."""
from __future__ import annotations

import asyncio
import base64
import os
from dataclasses import dataclass

DEFAULT_PROMPT = (
    "Describe what you see on this screen in 2-3 sentences. "
    "Focus on: what app is open, what content is visible, "
    "and any interactive elements (buttons, links, forms). Be concise."
)


def resolve_provider() -> tuple[str | None, str | None]:
    provider = os.environ.get("PUPPET_VISION_PROVIDER")
    model = os.environ.get("PUPPET_VISION_MODEL")
    return provider, model


PROVIDER_DEFAULTS = {
    "anthropic": ("claude-haiku-4-5-20251001", "ANTHROPIC_API_KEY"),
    "openai": ("gpt-4o-mini", "OPENAI_API_KEY"),
    "gemini": ("gemini-2.0-flash", "GEMINI_API_KEY"),
    "ollama": ("llava", None),
}


@dataclass
class VisionAgent:
    provider: str | None = None
    model: str | None = None
    prompt: str = DEFAULT_PROMPT
    _resolved: bool = False

    def _resolve(self) -> None:
        if self._resolved:
            return
        self._resolved = True
        if self.provider:
            return
        env_provider, env_model = resolve_provider()
        if env_provider:
            self.provider = env_provider
            self.model = env_model or PROVIDER_DEFAULTS.get(env_provider, (None, None))[0]

    async def analyze(self, image_bytes: bytes, prompt: str | None = None) -> str:
        self._resolve()
        prompt = prompt or self.prompt
        if not self.provider:
            return ""
        try:
            return await asyncio.wait_for(self._call_provider(image_bytes, prompt), timeout=15.0)
        except Exception:
            return ""

    async def _call_provider(self, image_bytes: bytes, prompt: str) -> str:
        b64 = base64.b64encode(image_bytes).decode()
        if self.provider == "anthropic":
            return await self._call_anthropic(b64, prompt)
        elif self.provider == "openai":
            return await self._call_openai(b64, prompt)
        elif self.provider == "gemini":
            return await self._call_gemini(b64, prompt)
        elif self.provider == "ollama":
            return await self._call_ollama(b64, prompt)
        return ""

    async def _call_anthropic(self, b64: str, prompt: str) -> str:
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic()
        msg = await client.messages.create(
            model=self.model or "claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
                {"type": "text", "text": prompt},
            ]}],
        )
        return msg.content[0].text

    async def _call_openai(self, b64: str, prompt: str) -> str:
        from openai import AsyncOpenAI
        client = AsyncOpenAI()
        resp = await client.chat.completions.create(
            model=self.model or "gpt-4o-mini",
            max_tokens=300,
            messages=[{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                {"type": "text", "text": prompt},
            ]}],
        )
        return resp.choices[0].message.content

    async def _call_gemini(self, b64: str, prompt: str) -> str:
        from google import genai
        client = genai.Client()
        resp = await client.aio.models.generate_content(
            model=self.model or "gemini-2.0-flash",
            contents=[genai.types.Part.from_bytes(data=base64.b64decode(b64), mime_type="image/jpeg"), prompt],
        )
        return resp.text

    async def _call_ollama(self, b64: str, prompt: str) -> str:
        import subprocess, json
        body = json.dumps({"model": self.model or "llava", "prompt": prompt, "images": [b64], "stream": False})
        proc = subprocess.run(["curl", "-s", "http://localhost:11434/api/generate", "-d", body], capture_output=True, text=True, timeout=15)
        data = json.loads(proc.stdout)
        return data.get("response", "")
