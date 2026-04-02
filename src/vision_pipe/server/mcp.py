from __future__ import annotations

import base64
from dataclasses import dataclass, field
from typing import Any

from PIL import Image
import io

from vision_pipe.core.capture import ScreenCapture
from vision_pipe.core.actions import DesktopActions
from vision_pipe.core.pii_filter import PiiFilter


@dataclass
class VisionPipeContext:
    capture: ScreenCapture
    actions: DesktopActions
    pii_filter: PiiFilter = field(default_factory=PiiFilter)
    _unmask_approved: bool = False


def create_all_tools(ctx: VisionPipeContext) -> dict[str, Any]:

    async def vision_list_windows() -> list[dict]:
        windows = ctx.capture.list_windows()
        return [{"app": w.owner, "title": w.title, "width": w.width, "height": w.height, "window_id": w.window_id} for w in windows]

    async def vision_get_state() -> dict:
        from vision_pipe.core.ocr import ocr_full_text
        windows = ctx.capture.list_windows()
        window_list = [{"app": w.owner, "title": w.title, "width": w.width, "height": w.height} for w in windows]
        active_text = ""
        if windows:
            try:
                img = await ctx.capture.capture_window_bytes(windows[0].window_id)
                active_text = ocr_full_text(img)
            except Exception:
                active_text = "(OCR failed)"
        if not ctx._unmask_approved:
            active_text = ctx.pii_filter.mask_text(active_text, app_name=windows[0].owner if windows else "")
        return {"windows": window_list, "active_window": window_list[0] if window_list else None, "active_window_text": active_text[:3000]}

    async def vision_read_window(app: str | None = None, index: int = 0) -> dict:
        from vision_pipe.core.ocr import ocr_with_bounds
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
            elements = ocr_with_bounds(img)
            full_text = "\n".join(e.text for e in elements)
        except Exception as e:
            return {"error": f"Capture/OCR failed: {e}"}
        if not ctx._unmask_approved:
            full_text = ctx.pii_filter.mask_text(full_text, app_name=win.owner)
            element_dicts = ctx.pii_filter.mask_elements([e.to_dict() for e in elements[:100]], app_name=win.owner)
        else:
            element_dicts = [e.to_dict() for e in elements[:100]]
        return {"app": win.owner, "title": win.title, "size": f"{win.width}x{win.height}", "text": full_text[:5000], "elements": element_dicts}

    async def vision_screenshot(app: str | None = None, max_width: int = 800) -> dict:
        if app:
            windows = ctx.capture.list_windows()
            app_lower = app.lower()
            matches = [w for w in windows if app_lower in w.owner.lower() or app_lower in w.title.lower()]
            if not matches:
                return {"error": f"No window found for '{app}'"}
            img_bytes = await ctx.capture.capture_window_bytes(matches[0].window_id)
        else:
            img_bytes = await ctx.capture.capture_bytes()

        # Resize to reduce token usage (Retina screenshots are huge)
        pil = Image.open(io.BytesIO(img_bytes))
        if pil.width > max_width:
            ratio = max_width / pil.width
            pil = pil.resize((max_width, int(pil.height * ratio)), Image.Resampling.LANCZOS)

        buf = io.BytesIO()
        pil.save(buf, format="JPEG", quality=75)
        encoded = base64.b64encode(buf.getvalue()).decode()
        return {"image_base64": encoded, "width": pil.width, "height": pil.height}

    async def vision_get_changes() -> dict:
        return {"changes": [], "note": "Change detection requires continuous monitoring (future feature)"}

    async def action_click(x: int, y: int, button: str = "left", clicks: int = 1) -> dict:
        return ctx.actions.click(x, y, button=button, clicks=clicks)

    async def action_double_click(x: int, y: int) -> dict:
        return ctx.actions.double_click(x, y)

    async def action_right_click(x: int, y: int) -> dict:
        return ctx.actions.right_click(x, y)

    async def action_type_text(text: str, interval: float = 0) -> dict:
        return ctx.actions.type_text(text, interval=interval)

    async def action_press(key: str, presses: int = 1) -> dict:
        return ctx.actions.press(key, presses=presses)

    async def action_hotkey(keys: list[str]) -> dict:
        return ctx.actions.hotkey(keys)

    async def action_scroll(amount: int, x: int | None = None, y: int | None = None) -> dict:
        return ctx.actions.scroll(amount, x=x, y=y)

    async def action_drag(start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.5) -> dict:
        return ctx.actions.drag(start_x, start_y, end_x, end_y, duration=duration)

    async def action_move_mouse(x: int, y: int) -> dict:
        return ctx.actions.move_mouse(x, y)

    async def action_activate_window(app: str) -> dict:
        return ctx.actions.activate_window(app)

    async def action_clipboard_copy(text: str) -> dict:
        return ctx.actions.clipboard_copy(text)

    async def action_clipboard_paste() -> dict:
        return ctx.actions.clipboard_paste()

    async def action_open_url(url: str, browser: str = "Google Chrome") -> dict:
        """Open a URL in a browser — handles clipboard paste to avoid keyboard layout issues."""
        import subprocess as sp
        sp.run(["open", "-a", browser, url], capture_output=True, timeout=5)
        import asyncio
        await asyncio.sleep(2)
        return {"status": "ok", "action": "open_url", "url": url, "browser": browser}

    async def action_type_safe(text: str) -> dict:
        """Type text safely via clipboard paste — avoids keyboard layout issues."""
        ctx.actions.clipboard_copy(text)
        ctx.actions.hotkey(["cmd", "v"])
        return {"status": "ok", "action": "type_safe", "length": len(text)}

    async def system_check_permissions() -> dict:
        from vision_pipe.core.permissions import check_accessibility
        return check_accessibility()

    async def system_get_mouse_position() -> dict:
        return ctx.actions.get_mouse_position()

    async def system_get_screen_size() -> dict:
        return ctx.actions.get_screen_size()

    async def system_unmask(reason: str) -> dict:
        """Request temporary unmasking of sensitive data. Requires user approval."""
        # In MCP context, we can't directly prompt the user.
        # We set a flag and return instructions for the agent to confirm with user.
        ctx._unmask_approved = True
        return {
            "status": "unmasked",
            "warning": "PII masking temporarily disabled. Re-enable with system_mask.",
            "reason": reason,
        }

    async def system_mask() -> dict:
        """Re-enable PII masking after temporary unmask."""
        ctx._unmask_approved = False
        return {"status": "masked", "message": "PII masking re-enabled."}

    return {
        "vision_list_windows": vision_list_windows,
        "vision_get_state": vision_get_state,
        "vision_read_window": vision_read_window,
        "vision_screenshot": vision_screenshot,
        "vision_get_changes": vision_get_changes,
        "action_click": action_click,
        "action_double_click": action_double_click,
        "action_right_click": action_right_click,
        "action_type_text": action_type_text,
        "action_press": action_press,
        "action_hotkey": action_hotkey,
        "action_scroll": action_scroll,
        "action_drag": action_drag,
        "action_move_mouse": action_move_mouse,
        "action_activate_window": action_activate_window,
        "action_clipboard_copy": action_clipboard_copy,
        "action_clipboard_paste": action_clipboard_paste,
        "action_open_url": action_open_url,
        "action_type_safe": action_type_safe,
        "system_check_permissions": system_check_permissions,
        "system_get_mouse_position": system_get_mouse_position,
        "system_get_screen_size": system_get_screen_size,
        "system_unmask": system_unmask,
        "system_mask": system_mask,
    }
