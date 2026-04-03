from __future__ import annotations

import io
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image


@dataclass
class WindowInfo:
    """Metadata about a captured window."""
    window_id: int
    owner: str
    title: str
    x: int
    y: int
    width: int
    height: int


class ScreenCapture:
    """Captures the macOS screen and individual windows.

    Uses CGWindowList via Quartz for per-window capture (no app switching)
    and screencapture CLI as fallback for full-screen capture.
    """

    async def capture(self) -> np.ndarray:
        """Capture the full main display as numpy array."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            tmp_path = f.name
        try:
            subprocess.run(
                ["screencapture", "-x", tmp_path],
                check=True, capture_output=True, timeout=5,
            )
            img = Image.open(tmp_path).convert("RGB")
            return np.array(img)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    async def capture_bytes(self) -> bytes:
        """Capture the full main display as PNG bytes."""
        frame = await self.capture()
        img = Image.fromarray(frame)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def list_windows(self, min_size: int = 100) -> list[WindowInfo]:
        """List all visible windows using Quartz CGWindowList.

        Returns windows sorted by front-to-back order (frontmost first).
        Skips windows smaller than min_size in either dimension.
        """
        import Quartz

        window_list = Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListOptionOnScreenOnly
            | Quartz.kCGWindowListExcludeDesktopElements,
            Quartz.kCGNullWindowID,
        )

        windows: list[WindowInfo] = []
        for w in window_list:
            layer = w.get("kCGWindowLayer", 0)
            if layer != 0:
                continue

            bounds = w.get("kCGWindowBounds", {})
            width = int(bounds.get("Width", 0))
            height = int(bounds.get("Height", 0))
            if width < min_size or height < min_size:
                continue

            windows.append(
                WindowInfo(
                    window_id=int(w.get("kCGWindowNumber", 0)),
                    owner=w.get("kCGWindowOwnerName", ""),
                    title=w.get("kCGWindowName", ""),
                    x=int(bounds.get("X", 0)),
                    y=int(bounds.get("Y", 0)),
                    width=width,
                    height=height,
                )
            )

        return windows

    async def capture_window(self, window_id: int) -> np.ndarray:
        """Capture a specific window by its CGWindow ID — no app switching needed."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            tmp_path = f.name
        try:
            subprocess.run(
                ["screencapture", "-l", str(window_id), "-x", tmp_path],
                check=True, capture_output=True, timeout=5,
            )
            img = Image.open(tmp_path).convert("RGB")
            return np.array(img)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    async def capture_window_bytes(self, window_id: int) -> bytes:
        """Capture a specific window as PNG bytes."""
        frame = await self.capture_window(window_id)
        img = Image.fromarray(frame)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    async def capture_all_windows(
        self, min_size: int = 100
    ) -> list[tuple[WindowInfo, bytes]]:
        """Capture ALL visible windows in one pass — no app switching.

        Returns list of (WindowInfo, png_bytes) sorted front-to-back.
        """
        windows = self.list_windows(min_size=min_size)
        results: list[tuple[WindowInfo, bytes]] = []
        for win in windows:
            png = await self.capture_window_bytes(win.window_id)
            results.append((win, png))
        return results
