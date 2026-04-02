from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from vision_pipe.core.world_model import WorldModel
from vision_pipe.types import FocusPriority


@dataclass
class VisionMCPContext:
    world_model: WorldModel
    peripheral: Any
    foveal: Any
    capture: Any


def create_vision_tools(ctx: VisionMCPContext) -> dict[str, Any]:

    async def get_state() -> dict:
        """Get current screen state: all windows + OCR of active window."""
        from vision_pipe.core.ocr import ocr_full_text

        windows = ctx.capture.list_windows()
        window_list = [
            {"app": w.owner, "title": w.title, "width": w.width, "height": w.height}
            for w in windows
        ]

        # OCR the frontmost window for text content
        active_text = ""
        if windows:
            try:
                img = await ctx.capture.capture_window_bytes(windows[0].window_id)
                active_text = ocr_full_text(img)
            except Exception:
                active_text = "(OCR failed)"

        return {
            "windows": window_list,
            "active_window": window_list[0] if window_list else None,
            "active_window_text": active_text[:3000],
        }

    async def read_window(app: str | None = None, index: int = 0) -> dict:
        """Read text content of a specific window via native OCR.

        Args:
            app: App name to find (e.g. "Chrome", "Safari", "Terminal"). Case-insensitive partial match.
            index: Which window if multiple matches (0 = first/frontmost).
        """
        from vision_pipe.core.ocr import ocr_full_text

        windows = ctx.capture.list_windows()

        if app:
            app_lower = app.lower()
            matches = [w for w in windows if app_lower in w.owner.lower() or app_lower in w.title.lower()]
        else:
            matches = windows

        if not matches:
            return {"error": f"No window found for '{app}'", "available": [w.owner for w in windows]}

        if index >= len(matches):
            index = 0

        win = matches[index]
        try:
            img = await ctx.capture.capture_window_bytes(win.window_id)
            text = ocr_full_text(img)
        except Exception as e:
            return {"error": f"Capture/OCR failed: {e}"}

        return {
            "app": win.owner,
            "title": win.title,
            "size": f"{win.width}x{win.height}",
            "text": text[:5000],
        }

    async def describe(region: str | None = None) -> dict:
        """Describe screen via VLM (requires working Ollama). Falls back to OCR."""
        try:
            image_bytes = await ctx.capture.capture_bytes()
            scan_result = await ctx.peripheral.scan(image_bytes)
            ctx.world_model.update_from_scan(scan_result)
            if region is None:
                return ctx.world_model.get_state().model_dump(mode="json")
            region_info = ctx.world_model.find_region(region)
            if region_info is None:
                return {"error": f"Region '{region}' not found"}
            focus_result = await ctx.foveal.focus(image_bytes, region_info, region)
            ctx.world_model.update_from_focus(focus_result)
            return focus_result.model_dump(mode="json")
        except Exception as e:
            # Fallback to OCR
            return await get_state()

    async def get_changes(since: str | None = None) -> dict:
        since_dt = None
        if since:
            since_dt = datetime.fromisoformat(since)
        changes = ctx.world_model.get_changes(since=since_dt)
        return {"changes": [c.model_dump(mode="json") for c in changes]}

    async def focus(region: str, priority: str = "high") -> dict:
        try:
            prio = FocusPriority(priority)
        except ValueError:
            return {"error": f"Invalid priority: {priority}"}
        ctx.world_model.set_focus(region, prio)
        return {"status": "ok", "region": region, "priority": priority}

    async def ignore(region: str) -> dict:
        ctx.world_model.set_focus(region, FocusPriority.IGNORED)
        return {"status": "ok", "region": region, "priority": "ignored"}

    return {
        "get_state": get_state,
        "read_window": read_window,
        "describe": describe,
        "get_changes": get_changes,
        "focus": focus,
        "ignore": ignore,
    }
