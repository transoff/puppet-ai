# src/vision_pipe/core/foveal.py
from __future__ import annotations
import io
from PIL import Image
from vision_pipe.providers.base import VisionProvider
from vision_pipe.types import FocusResult, RegionInfo


class FovealFocus:
    def __init__(self, provider: VisionProvider) -> None:
        self._provider = provider

    async def focus(self, image_bytes: bytes, region: RegionInfo, context: str) -> FocusResult:
        cropped = self._crop(image_bytes, region)
        return await self._provider.focus(cropped, region, context)

    def _crop(self, image_bytes: bytes, region: RegionInfo) -> bytes:
        img = Image.open(io.BytesIO(image_bytes))
        b = region.bounds
        cropped = img.crop((b.x, b.y, b.x + b.w, b.y + b.h))
        buf = io.BytesIO()
        cropped.save(buf, format="PNG")
        return buf.getvalue()
