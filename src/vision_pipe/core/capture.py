from __future__ import annotations
import io
import subprocess
import tempfile
from pathlib import Path
import numpy as np
from PIL import Image


class ScreenCapture:
    """Captures the macOS screen. Uses screencapture CLI."""

    async def capture(self) -> np.ndarray:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            tmp_path = f.name
        try:
            subprocess.run(["screencapture", "-x", "-C", tmp_path], check=True, capture_output=True, timeout=5)
            img = Image.open(tmp_path).convert("RGB")
            return np.array(img)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    async def capture_bytes(self) -> bytes:
        frame = await self.capture()
        img = Image.fromarray(frame)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
