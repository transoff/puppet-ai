# src/vision_pipe/core/peripheral.py
from __future__ import annotations
import io
from PIL import Image
from vision_pipe.providers.base import VisionProvider
from vision_pipe.types import ScanResult


class PeripheralVision:
    def __init__(self, provider: VisionProvider, resolution: tuple[int, int] = (512, 512)) -> None:
        self._provider = provider
        self._resolution = resolution

    async def scan(self, image_bytes: bytes) -> ScanResult:
        resized = self._resize(image_bytes)
        return await self._provider.scan(resized)

    def _resize(self, image_bytes: bytes) -> bytes:
        img = Image.open(io.BytesIO(image_bytes))
        if img.size != self._resolution:
            img = img.resize(self._resolution, Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
