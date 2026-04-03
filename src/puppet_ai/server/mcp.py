from __future__ import annotations

import base64
from dataclasses import dataclass, field
from typing import Any

from PIL import Image
import io

from puppet_ai.core.capture import ScreenCapture
from puppet_ai.core.actions import DesktopActions
from puppet_ai.core.pii_filter import PiiFilter
from puppet_ai.core.ocr_cache import OcrCache
from puppet_ai.core.cdp import CDPClient
from puppet_ai.core.vision_agent import VisionAgent


@dataclass
class VisionPipeContext:
    capture: ScreenCapture
    actions: DesktopActions
    pii_filter: PiiFilter = field(default_factory=PiiFilter)
    ocr_cache: OcrCache = field(default_factory=OcrCache)
    cdp: CDPClient = field(default_factory=CDPClient)
    vision_agent: VisionAgent = field(default_factory=VisionAgent)
    _unmask_approved: bool = False


def create_all_tools(ctx: VisionPipeContext) -> dict[str, Any]:

    async def vision_list_windows() -> list[dict]:
        windows = ctx.capture.list_windows()
        return [{"app": w.owner, "title": w.title, "width": w.width, "height": w.height, "window_id": w.window_id} for w in windows]

    async def vision_get_state() -> dict:
        from puppet_ai.core.ocr import ocr_full_text
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
        from puppet_ai.core.ocr import ocr_with_bounds
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
            pixel_hash = ctx.ocr_cache.compute_pixel_hash(img)
            cached = ctx.ocr_cache.get(win.window_id, pixel_hash)
            if cached is not None:
                cached["_cached"] = True
                return cached
            from puppet_ai.core.ocr import _get_retina_scale
            scale = _get_retina_scale()
            elements = ocr_with_bounds(
                img,
                window_x=int(win.x),
                window_y=int(win.y),
            )
            full_text = "\n".join(e.text for e in elements)
        except Exception as e:
            return {"error": f"Capture/OCR failed: {e}"}
        if not ctx._unmask_approved:
            full_text = ctx.pii_filter.mask_text(full_text, app_name=win.owner)
            element_dicts = ctx.pii_filter.mask_elements([e.to_dict() for e in elements[:100]], app_name=win.owner)
        else:
            element_dicts = [e.to_dict() for e in elements[:100]]
        result = {"app": win.owner, "title": win.title, "size": f"{win.width}x{win.height}", "text": full_text[:5000], "elements": element_dicts}
        ctx.ocr_cache.put(win.window_id, pixel_hash, result)
        return result

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
        jpeg_bytes = buf.getvalue()
        encoded = base64.b64encode(jpeg_bytes).decode()
        result = {"image_base64": encoded, "width": pil.width, "height": pil.height}
        ai_description = await ctx.vision_agent.analyze(jpeg_bytes)
        if ai_description:
            result["ai_description"] = ai_description
        return result

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

    async def action_scroll(amount: int, x: int | None = None, y: int | None = None, app: str | None = None) -> dict:
        """Scroll in an app. If app is specified, activates it and clicks center first."""
        if app:
            ctx.actions.activate_window(app)
            import asyncio
            await asyncio.sleep(0.3)
            # Click center of the app window to ensure focus
            windows = ctx.capture.list_windows()
            app_lower = app.lower()
            matches = [w for w in windows if app_lower in w.owner.lower()]
            if matches:
                from puppet_ai.core.ocr import _get_retina_scale
                scale = _get_retina_scale()
                win = matches[0]
                center_x = win.x + win.width // 2
                center_y = win.y + win.height // 2
                ctx.actions.click(center_x, center_y)
                await asyncio.sleep(0.1)
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

    _ALLOWED_BROWSERS = {"Google Chrome", "Safari", "Firefox", "Arc", "Brave Browser", "Microsoft Edge", "Opera", "Vivaldi", "Yandex Browser"}

    async def action_open_url(url: str, browser: str = "Google Chrome") -> dict:
        """Open a URL in a browser — handles clipboard paste to avoid keyboard layout issues."""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return {"error": f"Only http/https URLs allowed, got: {parsed.scheme}"}
        if browser not in _ALLOWED_BROWSERS:
            return {"error": f"Unknown browser: {browser}", "allowed": list(_ALLOWED_BROWSERS)}
        import subprocess as sp
        sp.run(["open", "-a", browser, url], capture_output=True, timeout=5)
        # Wait for page to start loading
        import asyncio
        await asyncio.sleep(1.5)
        # Return with OCR of the browser for immediate context
        try:
            windows = ctx.capture.list_windows()
            browser_lower = browser.lower()
            matches = [w for w in windows if browser_lower in w.owner.lower()]
            if matches:
                from puppet_ai.core.ocr import ocr_full_text
                img = await ctx.capture.capture_window_bytes(matches[0].window_id)
                page_text = ocr_full_text(img)
                return {"status": "ok", "action": "open_url", "url": url, "browser": browser, "page_preview": page_text[:1000]}
        except Exception:
            pass
        return {"status": "ok", "action": "open_url", "url": url, "browser": browser}

    async def action_type_safe(text: str) -> dict:
        """Type text safely via clipboard paste — avoids keyboard layout issues."""
        ctx.actions.clipboard_copy(text)
        ctx.actions.hotkey(["cmd", "v"])
        return {"status": "ok", "action": "type_safe", "length": len(text)}

    async def action_click_text(text: str, app: str | None = None, index: int = 0) -> dict:
        """Find text on screen via OCR and click its center. No need to calculate coordinates manually."""
        import asyncio
        from puppet_ai.core.ocr import ocr_with_bounds

        # Activate window first
        if app:
            ctx.actions.activate_window(app)
            await asyncio.sleep(0.3)

        windows = ctx.capture.list_windows()
        if app:
            app_lower = app.lower()
            matches = [w for w in windows if app_lower in w.owner.lower() or app_lower in w.title.lower()]
        else:
            matches = windows
        if not matches:
            return {"error": f"No window found for '{app}'"}

        win = matches[0]
        img = await ctx.capture.capture_window_bytes(win.window_id)
        from puppet_ai.core.ocr import _get_retina_scale
        scale = _get_retina_scale()
        elements = ocr_with_bounds(
            img,
            window_x=int(win.x),
            window_y=int(win.y),
        )

        text_lower = text.lower()
        found = [e for e in elements if text_lower in e.text.lower()]
        if not found:
            available = [e.text for e in elements[:20]]
            return {"error": f"Text '{text}' not found on screen", "visible_texts": available}

        if index >= len(found):
            index = 0

        target = found[index]
        cx, cy = target.center()
        ctx.actions.click(cx, cy)
        return {
            "status": "ok",
            "action": "click_text",
            "clicked": target.text,
            "x": cx,
            "y": cy,
            "matches_found": len(found),
        }

    async def system_check_permissions() -> dict:
        from puppet_ai.core.permissions import check_accessibility
        return check_accessibility()

    async def system_get_mouse_position() -> dict:
        return ctx.actions.get_mouse_position()

    async def system_get_screen_size() -> dict:
        return ctx.actions.get_screen_size()

    async def system_unmask(reason: str) -> dict:
        """Request temporary unmasking of sensitive data.

        WARNING: This disables PII masking immediately. There is no technical
        confirmation gate — it relies on the calling agent to ask the user first.
        Use only in trusted agent setups.
        """
        ctx._unmask_approved = True
        return {
            "status": "unmasked",
            "warning": "PII masking disabled. All sensitive data will be visible. Call system_mask to re-enable.",
            "reason": reason,
        }

    async def system_mask() -> dict:
        """Re-enable PII masking after temporary unmask."""
        ctx._unmask_approved = False
        return {"status": "masked", "message": "PII masking re-enabled."}

    async def vision_ui_elements(app: str | None = None, role_filter: str | None = None, max_depth: int = 5) -> dict:
        """Get UI elements (buttons, checkboxes, links) via Accessibility API."""
        from puppet_ai.core.accessibility import get_ui_elements
        if not app:
            windows = ctx.capture.list_windows()
            if windows:
                app = windows[0].owner
            else:
                return {"error": "No windows found"}
        elements = get_ui_elements(app, role_filter=role_filter, max_depth=max_depth)
        return {"app": app, "elements": [e.to_dict() for e in elements], "count": len(elements)}

    async def action_click_and_wait(text: str, app: str | None = None, timeout: float = 5.0) -> dict:
        """Click text and wait for screen to stabilize. Returns new screen state."""
        import asyncio
        from puppet_ai.core.accessibility import get_ui_elements
        from puppet_ai.core.ocr import ocr_with_bounds, ocr_full_text, _get_retina_scale
        from puppet_ai.core.wait import wait_for_stable

        # Activate window first to ensure it's visible and capturable
        if app:
            ctx.actions.activate_window(app)
            await asyncio.sleep(0.3)

        windows = ctx.capture.list_windows()
        if app:
            app_lower = app.lower()
            matches = [w for w in windows if app_lower in w.owner.lower() or app_lower in w.title.lower()]
        else:
            matches = windows
        if not matches:
            return {"error": f"No window found for '{app}'"}

        win = matches[0]
        text_lower = text.lower()
        click_x, click_y, source = None, None, ""

        # Try accessibility API first
        try:
            ax_elements = get_ui_elements(win.owner)
            ax_match = [e for e in ax_elements if text_lower in e.title.lower() or text_lower in e.value.lower()]
            if ax_match:
                click_x, click_y = ax_match[0].center()
                source = "accessibility"
        except Exception:
            pass

        # Fallback to OCR
        if click_x is None:
            try:
                img = await ctx.capture.capture_window_bytes(win.window_id)
                scale = _get_retina_scale()
                elements = ocr_with_bounds(img, window_x=win.x, window_y=win.y)
                ocr_match = [e for e in elements if text_lower in e.text.lower()]
                if ocr_match:
                    click_x, click_y = ocr_match[0].center()
                    source = "ocr"
            except Exception:
                pass

        if click_x is None:
            return {"error": f"Text '{text}' not found via accessibility or OCR"}

        # Click
        ctx.actions.click(click_x, click_y)

        # Wait for stable
        import asyncio
        await asyncio.sleep(0.3)

        async def capture_frame():
            return await ctx.capture.capture_window(win.window_id)

        waited, stable = await wait_for_stable(capture_frame, timeout=timeout)

        # OCR the new state
        try:
            new_img = await ctx.capture.capture_window_bytes(win.window_id)
            new_text = ocr_full_text(new_img)
        except Exception:
            new_text = ""

        return {
            "status": "ok",
            "action": "click_and_wait",
            "clicked": text,
            "x": click_x,
            "y": click_y,
            "source": source,
            "waited": round(waited, 2),
            "screen_stabilized": stable,
            "new_text_preview": new_text[:1000],
        }

    async def browser_navigate(url: str) -> dict:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return {"error": f"Only http/https URLs allowed, got: {parsed.scheme}"}
        try:
            await ctx.cdp.navigate(url)
            text = await ctx.cdp.evaluate("document.title")
            return {"status": "ok", "action": "browser_navigate", "url": url, "title": str(text)}
        except ConnectionError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"CDP error: {e}"}

    async def browser_fill(selector: str, value: str) -> dict:
        try:
            import json as _json
            js = f"""
            (function() {{
                var el = document.querySelector({_json.dumps(selector)});
                if (!el) return {{error: 'Element not found: ' + {_json.dumps(selector)}}};
                el.focus();
                el.value = {_json.dumps(value)};
                el.dispatchEvent(new Event('input', {{bubbles: true}}));
                el.dispatchEvent(new Event('change', {{bubbles: true}}));
                return {{status: 'ok', tag: el.tagName, id: el.id}};
            }})()
            """
            result = await ctx.cdp.evaluate(js)
            if isinstance(result, dict) and result.get("error"):
                return result
            return {"status": "ok", "action": "browser_fill", "selector": selector, "length": len(value)}
        except ConnectionError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"CDP error: {e}"}

    async def browser_click(selector: str) -> dict:
        try:
            import json as _json
            js = f"""
            (function() {{
                var el = document.querySelector({_json.dumps(selector)});
                if (!el) return {{error: 'Element not found: ' + {_json.dumps(selector)}}};
                el.click();
                return {{status: 'ok', tag: el.tagName, text: el.innerText ? el.innerText.substring(0, 100) : ''}};
            }})()
            """
            result = await ctx.cdp.evaluate(js)
            if isinstance(result, dict) and result.get("error"):
                return result
            return {"status": "ok", "action": "browser_click", "selector": selector}
        except ConnectionError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"CDP error: {e}"}

    async def browser_get_text() -> dict:
        try:
            text = await ctx.cdp.evaluate("document.body.innerText")
            title = await ctx.cdp.evaluate("document.title")
            url = await ctx.cdp.evaluate("window.location.href")
            return {"status": "ok", "title": str(title), "url": str(url), "text": str(text)[:5000]}
        except ConnectionError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"CDP error: {e}"}

    async def browser_evaluate(js: str) -> dict:
        try:
            result = await ctx.cdp.evaluate(js)
            return {"status": "ok", "result": str(result)[:3000]}
        except ConnectionError as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"CDP error: {e}"}

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
        "action_click_text": action_click_text,
        "system_check_permissions": system_check_permissions,
        "system_get_mouse_position": system_get_mouse_position,
        "system_get_screen_size": system_get_screen_size,
        "system_unmask": system_unmask,
        "system_mask": system_mask,
        "vision_ui_elements": vision_ui_elements,
        "action_click_and_wait": action_click_and_wait,
        "browser_navigate": browser_navigate,
        "browser_fill": browser_fill,
        "browser_click": browser_click,
        "browser_get_text": browser_get_text,
        "browser_evaluate": browser_evaluate,
    }
