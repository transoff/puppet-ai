# vision-pipe v2: Hands Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add computer control (mouse, keyboard, clipboard, window management) to the vision-pipe MCP server, with OCR bounding boxes for click targets and a system prompt for agent onboarding.

**Architecture:** Extend existing MCP server with `action_*` tools (pyautogui), `system_*` tools (permissions/screen info), upgrade OCR to return bounding boxes, add `vision_screenshot` for foveal pass-through, rename existing tools with `vision_` prefix, and inject MCP instructions.

**Tech Stack:** pyautogui (mouse/keyboard), pyperclip (clipboard), pyobjc-framework-Vision (OCR with bounds), existing MCP server infrastructure

**Spec:** `docs/superpowers/specs/2026-04-02-vision-pipe-hands-design.md`

---

## File Structure

```
src/vision_pipe/
├── core/
│   ├── ocr.py              # MODIFY: add ocr_with_bounds() returning text + coordinates
│   ├── actions.py           # CREATE: DesktopActions class wrapping pyautogui
│   ├── permissions.py       # CREATE: check_accessibility_permissions()
│   └── capture.py           # existing, no changes
├── server/
│   └── mcp.py              # REWRITE: new tool registry with vision_*, action_*, system_*
├── cli.py                   # MODIFY: update serve to register all tools + instructions
└── instructions.py          # CREATE: MCP instructions text

tests/
├── test_ocr_bounds.py       # CREATE: OCR bounding box tests
├── test_actions.py          # CREATE: action module tests (mocked pyautogui)
├── test_permissions.py      # CREATE: permission check tests
├── test_mcp_v2.py           # CREATE: full MCP v2 tool tests
└── test_instructions.py     # CREATE: instructions content test
```

---

### Task 1: OCR with Bounding Boxes

**Files:**
- Modify: `src/vision_pipe/core/ocr.py`
- Create: `tests/test_ocr_bounds.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_ocr_bounds.py
from __future__ import annotations

import pytest
from PIL import Image, ImageDraw, ImageFont
import io

from vision_pipe.core.ocr import ocr_with_bounds, OcrElement


@pytest.fixture
def image_with_text() -> bytes:
    """Create a 400x200 image with 'Hello World' text."""
    img = Image.new("RGB", (400, 200), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((50, 80), "Hello World", fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_ocr_with_bounds_returns_elements(image_with_text):
    elements = ocr_with_bounds(image_with_text)
    assert len(elements) > 0
    assert all(isinstance(e, OcrElement) for e in elements)


def test_ocr_element_has_text_and_coords(image_with_text):
    elements = ocr_with_bounds(image_with_text)
    for elem in elements:
        assert isinstance(elem.text, str)
        assert len(elem.text) > 0
        assert isinstance(elem.x, int)
        assert isinstance(elem.y, int)
        assert isinstance(elem.w, int)
        assert isinstance(elem.h, int)
        assert elem.w > 0
        assert elem.h > 0


def test_ocr_element_center(image_with_text):
    elements = ocr_with_bounds(image_with_text)
    if elements:
        e = elements[0]
        cx, cy = e.center()
        assert cx == e.x + e.w // 2
        assert cy == e.y + e.h // 2


def test_ocr_with_bounds_empty_image():
    img = Image.new("RGB", (100, 100), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    elements = ocr_with_bounds(buf.getvalue())
    assert elements == []


def test_ocr_element_serialization(image_with_text):
    elements = ocr_with_bounds(image_with_text)
    if elements:
        d = elements[0].to_dict()
        assert "text" in d
        assert "x" in d
        assert "y" in d
        assert "w" in d
        assert "h" in d
```

- [ ] **Step 2: Run tests to verify failure**

Run: `.venv/bin/python -m pytest tests/test_ocr_bounds.py -v`
Expected: FAIL — `ImportError: cannot import name 'ocr_with_bounds'`

- [ ] **Step 3: Implement ocr_with_bounds**

Add to `src/vision_pipe/core/ocr.py`:

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class OcrElement:
    """A text element with its bounding box in screen coordinates."""
    text: str
    x: int
    y: int
    w: int
    h: int

    def center(self) -> tuple[int, int]:
        return self.x + self.w // 2, self.y + self.h // 2

    def to_dict(self) -> dict:
        return {"text": self.text, "x": self.x, "y": self.y, "w": self.w, "h": self.h}


def ocr_with_bounds(
    image_bytes: bytes,
    languages: list[str] | None = None,
    image_width: int | None = None,
    image_height: int | None = None,
) -> list[OcrElement]:
    """Run OCR and return text elements with bounding boxes.

    Apple Vision returns normalized coordinates (0-1).
    We convert to pixel coordinates using image dimensions.
    """
    import Vision
    from Foundation import NSData

    if languages is None:
        languages = ["ru", "en"]

    # Get image dimensions if not provided
    if image_width is None or image_height is None:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(image_bytes))
        image_width, image_height = img.size

    ns_data = NSData.dataWithBytes_length_(image_bytes, len(image_bytes))
    handler = Vision.VNImageRequestHandler.alloc().initWithData_options_(ns_data, None)
    request = Vision.VNRecognizeTextRequest.alloc().init()
    request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    request.setRecognitionLanguages_(languages)

    success, error = handler.performRequests_error_([request], None)
    if not success:
        return []

    results = request.results() or []
    elements: list[OcrElement] = []

    for obs in results:
        candidates = obs.topCandidates_(1)
        if not candidates:
            continue
        text = candidates[0].string()
        bbox = obs.boundingBox()

        # Apple Vision: origin is bottom-left, normalized 0-1
        # Convert to top-left origin, pixel coordinates
        x = int(bbox.origin.x * image_width)
        y = int((1 - bbox.origin.y - bbox.size.height) * image_height)
        w = int(bbox.size.width * image_width)
        h = int(bbox.size.height * image_height)

        elements.append(OcrElement(text=text, x=x, y=y, w=w, h=h))

    return elements


def ocr_from_png(image_bytes: bytes, languages: list[str] | None = None) -> list[str]:
    """Run OCR on PNG image bytes. Returns list of text blocks."""
    elements = ocr_with_bounds(image_bytes, languages)
    return [e.text for e in elements]


def ocr_full_text(image_bytes: bytes, languages: list[str] | None = None) -> str:
    """Run OCR and return all text joined as a single string."""
    blocks = ocr_from_png(image_bytes, languages)
    return "\n".join(blocks)
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_ocr_bounds.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/vision_pipe/core/ocr.py tests/test_ocr_bounds.py
git commit -m "feat: OCR with bounding boxes — text + coordinates for click targets"
```

---

### Task 2: Desktop Actions Module

**Files:**
- Create: `src/vision_pipe/core/actions.py`
- Create: `tests/test_actions.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_actions.py
from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from vision_pipe.core.actions import DesktopActions


@pytest.fixture
def actions():
    with patch("vision_pipe.core.actions.pyautogui") as mock_pag:
        mock_pag.size.return_value = (1920, 1080)
        mock_pag.position.return_value = (500, 300)
        da = DesktopActions(failsafe=True)
        da._pag = mock_pag
        yield da, mock_pag


def test_click(actions):
    da, mock = actions
    result = da.click(100, 200)
    mock.click.assert_called_once_with(100, 200, button="left", clicks=1)
    assert result["status"] == "ok"


def test_click_right_button(actions):
    da, mock = actions
    da.click(100, 200, button="right")
    mock.click.assert_called_once_with(100, 200, button="right", clicks=1)


def test_double_click(actions):
    da, mock = actions
    da.double_click(300, 400)
    mock.click.assert_called_once_with(300, 400, button="left", clicks=2)


def test_type_text(actions):
    da, mock = actions
    da.type_text("hello")
    mock.write.assert_called_once_with("hello", interval=0)


def test_press_key(actions):
    da, mock = actions
    da.press("enter")
    mock.press.assert_called_once_with("enter", presses=1)


def test_hotkey(actions):
    da, mock = actions
    da.hotkey(["cmd", "c"])
    mock.hotkey.assert_called_once_with("cmd", "c")


def test_scroll(actions):
    da, mock = actions
    da.scroll(-5)
    mock.scroll.assert_called_once_with(-5)


def test_scroll_at_position(actions):
    da, mock = actions
    da.scroll(3, x=100, y=200)
    mock.scroll.assert_called_once_with(3, x=100, y=200)


def test_drag(actions):
    da, mock = actions
    da.drag(100, 200, 300, 400)
    mock.moveTo.assert_called_once_with(100, 200)
    mock.drag.assert_called_once()


def test_move_mouse(actions):
    da, mock = actions
    da.move_mouse(500, 600)
    mock.moveTo.assert_called_once_with(500, 600, duration=0)


def test_get_mouse_position(actions):
    da, mock = actions
    pos = da.get_mouse_position()
    assert pos == {"x": 500, "y": 300}


def test_get_screen_size(actions):
    da, mock = actions
    size = da.get_screen_size()
    assert size == {"width": 1920, "height": 1080}


def test_clipboard_copy(actions):
    da, _ = actions
    with patch("vision_pipe.core.actions.pyperclip") as mock_clip:
        da.clipboard_copy("test")
        mock_clip.copy.assert_called_once_with("test")


def test_clipboard_paste(actions):
    da, _ = actions
    with patch("vision_pipe.core.actions.pyperclip") as mock_clip:
        mock_clip.paste.return_value = "pasted"
        result = da.clipboard_paste()
        assert result["text"] == "pasted"


def test_activate_window(actions):
    da, _ = actions
    with patch("vision_pipe.core.actions.subprocess") as mock_sub:
        mock_sub.run.return_value = MagicMock(returncode=0)
        result = da.activate_window("Chrome")
        assert result["status"] == "ok"
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/test_actions.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement DesktopActions**

```python
# src/vision_pipe/core/actions.py
"""Desktop control actions via pyautogui.

Provides mouse, keyboard, scroll, drag, clipboard, and window management.
All methods return a dict with status for MCP tool responses.
"""
from __future__ import annotations

import subprocess

import pyautogui
import pyperclip


class DesktopActions:
    """Wraps pyautogui for computer control. All methods return dicts."""

    def __init__(self, failsafe: bool = True) -> None:
        pyautogui.FAILSAFE = failsafe
        self._pag = pyautogui

    def click(
        self, x: int, y: int, button: str = "left", clicks: int = 1
    ) -> dict:
        self._pag.click(x, y, button=button, clicks=clicks)
        return {"status": "ok", "action": "click", "x": x, "y": y, "button": button}

    def double_click(self, x: int, y: int) -> dict:
        self._pag.click(x, y, button="left", clicks=2)
        return {"status": "ok", "action": "double_click", "x": x, "y": y}

    def right_click(self, x: int, y: int) -> dict:
        self._pag.click(x, y, button="right", clicks=1)
        return {"status": "ok", "action": "right_click", "x": x, "y": y}

    def type_text(self, text: str, interval: float = 0) -> dict:
        self._pag.write(text, interval=interval)
        return {"status": "ok", "action": "type_text", "length": len(text)}

    def press(self, key: str, presses: int = 1) -> dict:
        self._pag.press(key, presses=presses)
        return {"status": "ok", "action": "press", "key": key}

    def hotkey(self, keys: list[str]) -> dict:
        self._pag.hotkey(*keys)
        return {"status": "ok", "action": "hotkey", "keys": keys}

    def scroll(
        self, amount: int, x: int | None = None, y: int | None = None
    ) -> dict:
        kwargs = {}
        if x is not None:
            kwargs["x"] = x
        if y is not None:
            kwargs["y"] = y
        self._pag.scroll(amount, **kwargs)
        return {"status": "ok", "action": "scroll", "amount": amount}

    def drag(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration: float = 0.5,
    ) -> dict:
        self._pag.moveTo(start_x, start_y)
        self._pag.drag(
            end_x - start_x, end_y - start_y, duration=duration, button="left"
        )
        return {
            "status": "ok",
            "action": "drag",
            "from": [start_x, start_y],
            "to": [end_x, end_y],
        }

    def move_mouse(self, x: int, y: int, duration: float = 0) -> dict:
        self._pag.moveTo(x, y, duration=duration)
        return {"status": "ok", "action": "move_mouse", "x": x, "y": y}

    def get_mouse_position(self) -> dict:
        x, y = self._pag.position()
        return {"x": x, "y": y}

    def get_screen_size(self) -> dict:
        w, h = self._pag.size()
        return {"width": w, "height": h}

    def activate_window(self, app: str) -> dict:
        result = subprocess.run(
            [
                "osascript",
                "-e",
                f'tell application "{app}" to activate',
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return {"status": "ok", "action": "activate_window", "app": app}
        return {"status": "error", "error": result.stderr.strip()}

    def clipboard_copy(self, text: str) -> dict:
        pyperclip.copy(text)
        return {"status": "ok", "action": "clipboard_copy"}

    def clipboard_paste(self) -> dict:
        text = pyperclip.paste()
        return {"status": "ok", "action": "clipboard_paste", "text": text}
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_actions.py -v`
Expected: All 15 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/vision_pipe/core/actions.py tests/test_actions.py
git commit -m "feat: DesktopActions — mouse, keyboard, scroll, drag, clipboard, window control"
```

---

### Task 3: Permissions Check

**Files:**
- Create: `src/vision_pipe/core/permissions.py`
- Create: `tests/test_permissions.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_permissions.py
from vision_pipe.core.permissions import check_accessibility


def test_check_accessibility_returns_dict():
    result = check_accessibility()
    assert "accessible" in result
    assert isinstance(result["accessible"], bool)


def test_check_accessibility_has_instructions():
    result = check_accessibility()
    if not result["accessible"]:
        assert "instructions" in result
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/test_permissions.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement**

```python
# src/vision_pipe/core/permissions.py
"""Check macOS accessibility permissions for computer control."""
from __future__ import annotations


def check_accessibility() -> dict:
    """Check if the process has macOS Accessibility permissions.

    Returns dict with 'accessible' bool and instructions if not.
    """
    try:
        import Quartz

        trusted = Quartz.AXIsProcessTrusted()
        if trusted:
            return {"accessible": True}
        return {
            "accessible": False,
            "instructions": (
                "Accessibility access required for mouse/keyboard control. "
                "Go to System Settings → Privacy & Security → Accessibility "
                "and add this application (Terminal or your IDE)."
            ),
        }
    except ImportError:
        return {
            "accessible": False,
            "instructions": "pyobjc-framework-Quartz not installed. Run: pip install pyobjc-framework-Quartz",
        }
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_permissions.py -v`
Expected: All 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/vision_pipe/core/permissions.py tests/test_permissions.py
git commit -m "feat: accessibility permission check for action tools"
```

---

### Task 4: MCP Instructions

**Files:**
- Create: `src/vision_pipe/instructions.py`
- Create: `tests/test_instructions.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_instructions.py
from vision_pipe.instructions import MCP_INSTRUCTIONS


def test_instructions_is_string():
    assert isinstance(MCP_INSTRUCTIONS, str)
    assert len(MCP_INSTRUCTIONS) > 100


def test_instructions_contains_vision_tools():
    assert "vision_list_windows" in MCP_INSTRUCTIONS
    assert "vision_read_window" in MCP_INSTRUCTIONS
    assert "vision_screenshot" in MCP_INSTRUCTIONS


def test_instructions_contains_action_tools():
    assert "action_click" in MCP_INSTRUCTIONS
    assert "action_type_text" in MCP_INSTRUCTIONS
    assert "action_hotkey" in MCP_INSTRUCTIONS


def test_instructions_contains_workflow():
    assert "LOOK" in MCP_INSTRUCTIONS
    assert "ACT" in MCP_INSTRUCTIONS


def test_instructions_contains_coordinate_hint():
    assert "center" in MCP_INSTRUCTIONS.lower() or "bounding box" in MCP_INSTRUCTIONS.lower()
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/test_instructions.py -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement**

```python
# src/vision_pipe/instructions.py
"""MCP server instructions — sent to agents on connection."""

MCP_INSTRUCTIONS = """vision-pipe: Human-like computer perception and control for AI agents.

WHAT THIS IS:
You have eyes and hands. You can see everything on the user's screen and interact with any application — click, type, scroll, drag. Use this when the user asks you to do something on their computer, research information in the browser, check an app, or interact with any UI.

WHAT YOU CAN SEE (vision_* tools):
- vision_list_windows — all open windows (app name, title, size)
- vision_get_state — current screen: window list + text of active window
- vision_read_window(app) — read all text in a specific app via OCR (includes element coordinates for clicking)
- vision_screenshot(app) — get screenshot as base64 image (use if you can process images for detailed visual analysis)
- vision_get_changes — what changed on screen since last check

WHAT YOU CAN DO (action_* tools):
- action_click(x, y) — click at screen coordinates
- action_double_click(x, y) — double click
- action_right_click(x, y) — right click
- action_type_text(text) — type text at cursor position
- action_press(key) — press a key (enter, tab, escape, etc.)
- action_hotkey(keys) — keyboard shortcut (["cmd","c"], ["cmd","tab"], etc.)
- action_scroll(amount) — scroll up (positive) / down (negative)
- action_drag(start_x, start_y, end_x, end_y) — drag and drop
- action_move_mouse(x, y) — move cursor without clicking
- action_activate_window(app) — bring app to front
- action_clipboard_copy(text) / action_clipboard_paste() — clipboard operations

SYSTEM TOOLS:
- system_check_permissions — check if accessibility access is granted
- system_get_mouse_position — current cursor coordinates
- system_get_screen_size — screen dimensions in pixels

HOW TO WORK:
1. LOOK — see what's on screen (vision_list_windows → vision_read_window)
2. DECIDE — plan your next action based on what you see
3. ACT — perform one action (action_click, action_type_text, etc.)
4. LOOK — verify the action worked
5. REPEAT until task is complete

CHOOSING HOW TO LOOK:
- For text-heavy content: use vision_read_window (OCR with coordinates) — fast, always works
- If you can process images: use vision_screenshot for detailed visual analysis (foveal focus)
- Always prefer vision_read_window first — it gives you text AND click coordinates

FINDING CLICK TARGETS:
vision_read_window returns elements with bounding boxes: {"text": "Sign In", "x": 540, "y": 320, "w": 80, "h": 24}
To click "Sign In": action_click(580, 332) — click the center of the bounding box (x + w/2, y + h/2).

IMPORTANT:
- Always LOOK before acting — you need coordinates
- Always LOOK after acting — verify it worked
- Call action_activate_window(app) before interacting with a background app
- If system_check_permissions reports errors, tell the user to enable Accessibility access
- Coordinates are screen pixels. (0,0) = top-left corner.
- You are a tool — execute what the user or main agent asks. Report what you see, don't make autonomous decisions."""
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_instructions.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/vision_pipe/instructions.py tests/test_instructions.py
git commit -m "feat: MCP instructions — agent onboarding prompt for vision + actions"
```

---

### Task 5: MCP Server v2 — All Tools + Instructions

**Files:**
- Rewrite: `src/vision_pipe/server/mcp.py`
- Modify: `src/vision_pipe/cli.py`
- Create: `tests/test_mcp_v2.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_mcp_v2.py
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from vision_pipe.server.mcp import create_all_tools, VisionPipeContext


@pytest.fixture
def mock_capture():
    cap = MagicMock()
    cap.list_windows.return_value = [
        MagicMock(window_id=1, owner="Chrome", title="Google", width=1200, height=800),
    ]
    cap.capture_window_bytes = AsyncMock(return_value=b"fake_png")
    cap.capture_bytes = AsyncMock(return_value=b"fake_png")
    return cap


@pytest.fixture
def mock_actions():
    act = MagicMock()
    act.click.return_value = {"status": "ok", "action": "click"}
    act.type_text.return_value = {"status": "ok", "action": "type_text"}
    act.press.return_value = {"status": "ok", "action": "press"}
    act.hotkey.return_value = {"status": "ok", "action": "hotkey"}
    act.scroll.return_value = {"status": "ok", "action": "scroll"}
    act.double_click.return_value = {"status": "ok", "action": "double_click"}
    act.right_click.return_value = {"status": "ok", "action": "right_click"}
    act.drag.return_value = {"status": "ok", "action": "drag"}
    act.move_mouse.return_value = {"status": "ok", "action": "move_mouse"}
    act.activate_window.return_value = {"status": "ok", "action": "activate_window"}
    act.clipboard_copy.return_value = {"status": "ok", "action": "clipboard_copy"}
    act.clipboard_paste.return_value = {"status": "ok", "action": "clipboard_paste", "text": "hello"}
    act.get_mouse_position.return_value = {"x": 100, "y": 200}
    act.get_screen_size.return_value = {"width": 1920, "height": 1080}
    return act


@pytest.fixture
def ctx(mock_capture, mock_actions):
    return VisionPipeContext(capture=mock_capture, actions=mock_actions)


def test_create_all_tools_returns_dict(ctx):
    tools = create_all_tools(ctx)
    assert isinstance(tools, dict)
    assert len(tools) > 15


def test_vision_tools_present(ctx):
    tools = create_all_tools(ctx)
    assert "vision_list_windows" in tools
    assert "vision_get_state" in tools
    assert "vision_read_window" in tools
    assert "vision_screenshot" in tools


def test_action_tools_present(ctx):
    tools = create_all_tools(ctx)
    assert "action_click" in tools
    assert "action_type_text" in tools
    assert "action_press" in tools
    assert "action_hotkey" in tools
    assert "action_scroll" in tools
    assert "action_drag" in tools
    assert "action_activate_window" in tools


def test_system_tools_present(ctx):
    tools = create_all_tools(ctx)
    assert "system_check_permissions" in tools
    assert "system_get_mouse_position" in tools
    assert "system_get_screen_size" in tools


@pytest.mark.asyncio
async def test_vision_list_windows(ctx):
    tools = create_all_tools(ctx)
    result = await tools["vision_list_windows"]()
    assert len(result) == 1
    assert result[0]["app"] == "Chrome"


@pytest.mark.asyncio
async def test_action_click(ctx):
    tools = create_all_tools(ctx)
    result = await tools["action_click"](x=100, y=200)
    assert result["status"] == "ok"
    ctx.actions.click.assert_called_once_with(100, 200, button="left", clicks=1)


@pytest.mark.asyncio
async def test_action_type_text(ctx):
    tools = create_all_tools(ctx)
    result = await tools["action_type_text"](text="hello")
    assert result["status"] == "ok"


@pytest.mark.asyncio
async def test_action_hotkey(ctx):
    tools = create_all_tools(ctx)
    result = await tools["action_hotkey"](keys=["cmd", "c"])
    assert result["status"] == "ok"


@pytest.mark.asyncio
async def test_system_get_mouse_position(ctx):
    tools = create_all_tools(ctx)
    result = await tools["system_get_mouse_position"]()
    assert result["x"] == 100


@pytest.mark.asyncio
async def test_vision_screenshot(ctx):
    tools = create_all_tools(ctx)
    with patch("vision_pipe.server.mcp.base64") as mock_b64:
        mock_b64.b64encode.return_value = b"aW1hZ2U="
        result = await tools["vision_screenshot"](app="Chrome")
        assert "image_base64" in result
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/test_mcp_v2.py -v`
Expected: FAIL — import errors

- [ ] **Step 3: Rewrite mcp.py**

```python
# src/vision_pipe/server/mcp.py
"""MCP server tools — vision, actions, system."""
from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any

from vision_pipe.core.capture import ScreenCapture
from vision_pipe.core.actions import DesktopActions


@dataclass
class VisionPipeContext:
    capture: ScreenCapture
    actions: DesktopActions


def create_all_tools(ctx: VisionPipeContext) -> dict[str, Any]:
    """Create all MCP tool handlers: vision_*, action_*, system_*."""

    # ── VISION TOOLS ──

    async def vision_list_windows() -> list[dict]:
        windows = ctx.capture.list_windows()
        return [
            {"app": w.owner, "title": w.title, "width": w.width,
             "height": w.height, "window_id": w.window_id}
            for w in windows
        ]

    async def vision_get_state() -> dict:
        from vision_pipe.core.ocr import ocr_full_text

        windows = ctx.capture.list_windows()
        window_list = [
            {"app": w.owner, "title": w.title, "width": w.width, "height": w.height}
            for w in windows
        ]
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

    async def vision_read_window(app: str | None = None, index: int = 0) -> dict:
        from vision_pipe.core.ocr import ocr_with_bounds, ocr_full_text

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

        return {
            "app": win.owner,
            "title": win.title,
            "size": f"{win.width}x{win.height}",
            "text": full_text[:5000],
            "elements": [e.to_dict() for e in elements[:100]],
        }

    async def vision_screenshot(app: str | None = None, region: str | None = None) -> dict:
        if app:
            windows = ctx.capture.list_windows()
            app_lower = app.lower()
            matches = [w for w in windows if app_lower in w.owner.lower() or app_lower in w.title.lower()]
            if not matches:
                return {"error": f"No window found for '{app}'"}
            img = await ctx.capture.capture_window_bytes(matches[0].window_id)
        else:
            img = await ctx.capture.capture_bytes()

        encoded = base64.b64encode(img).decode()
        from PIL import Image
        import io
        pil = Image.open(io.BytesIO(img))
        return {
            "image_base64": encoded,
            "width": pil.width,
            "height": pil.height,
        }

    async def vision_get_changes() -> dict:
        return {"changes": [], "note": "Change detection requires continuous monitoring (future feature)"}

    # ── ACTION TOOLS ──

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

    # ── SYSTEM TOOLS ──

    async def system_check_permissions() -> dict:
        from vision_pipe.core.permissions import check_accessibility
        return check_accessibility()

    async def system_get_mouse_position() -> dict:
        return ctx.actions.get_mouse_position()

    async def system_get_screen_size() -> dict:
        return ctx.actions.get_screen_size()

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
        "system_check_permissions": system_check_permissions,
        "system_get_mouse_position": system_get_mouse_position,
        "system_get_screen_size": system_get_screen_size,
    }
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_mcp_v2.py -v`
Expected: All 11 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/vision_pipe/server/mcp.py tests/test_mcp_v2.py
git commit -m "feat: MCP server v2 — 20 tools (vision + action + system) with prefixes"
```

---

### Task 6: CLI + Tool Registration + Instructions

**Files:**
- Modify: `src/vision_pipe/cli.py`
- Modify: `pyproject.toml` (add dependencies)

- [ ] **Step 1: Update pyproject.toml dependencies**

Add to `pyproject.toml` in `[project]` dependencies:

```toml
dependencies = [
    "mcp>=1.0.0",
    "numpy>=1.24",
    "Pillow>=10.0",
    "pydantic>=2.0",
    "pyyaml>=6.0",
    "click>=8.0",
    "httpx>=0.27",
    "pyautogui>=0.9",
    "pyperclip>=1.8",
]
```

- [ ] **Step 2: Rewrite _run_mcp_server in cli.py**

Replace the `_run_mcp_server` async function and the `list_tools`/`call_tool` handlers in `src/vision_pipe/cli.py`:

```python
async def _run_mcp_server(cfg):
    """Run the MCP server on stdio with all vision + action + system tools."""
    import json
    import sys

    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import TextContent, Tool

    from vision_pipe.core.actions import DesktopActions
    from vision_pipe.core.capture import ScreenCapture
    from vision_pipe.instructions import MCP_INSTRUCTIONS
    from vision_pipe.server.mcp import VisionPipeContext, create_all_tools

    capture = ScreenCapture()
    actions = DesktopActions(failsafe=True)
    ctx = VisionPipeContext(capture=capture, actions=actions)
    tools = create_all_tools(ctx)

    server = Server("vision-pipe")

    TOOL_SCHEMAS = {
        "vision_list_windows": {"type": "object", "properties": {}},
        "vision_get_state": {"type": "object", "properties": {}},
        "vision_read_window": {"type": "object", "properties": {
            "app": {"type": "string", "description": "App name (partial match)"},
            "index": {"type": "integer", "description": "Window index if multiple matches (default 0)"},
        }},
        "vision_screenshot": {"type": "object", "properties": {
            "app": {"type": "string", "description": "App name, or omit for full screen"},
        }},
        "vision_get_changes": {"type": "object", "properties": {}},
        "action_click": {"type": "object", "properties": {
            "x": {"type": "integer"}, "y": {"type": "integer"},
            "button": {"type": "string", "enum": ["left", "right", "middle"]},
            "clicks": {"type": "integer"},
        }, "required": ["x", "y"]},
        "action_double_click": {"type": "object", "properties": {
            "x": {"type": "integer"}, "y": {"type": "integer"},
        }, "required": ["x", "y"]},
        "action_right_click": {"type": "object", "properties": {
            "x": {"type": "integer"}, "y": {"type": "integer"},
        }, "required": ["x", "y"]},
        "action_type_text": {"type": "object", "properties": {
            "text": {"type": "string"},
            "interval": {"type": "number", "description": "Seconds between keystrokes (0=instant)"},
        }, "required": ["text"]},
        "action_press": {"type": "object", "properties": {
            "key": {"type": "string", "description": "Key name: enter, tab, escape, space, up, down, etc."},
            "presses": {"type": "integer"},
        }, "required": ["key"]},
        "action_hotkey": {"type": "object", "properties": {
            "keys": {"type": "array", "items": {"type": "string"}, "description": 'Keys to press together, e.g. ["cmd","c"]'},
        }, "required": ["keys"]},
        "action_scroll": {"type": "object", "properties": {
            "amount": {"type": "integer", "description": "Scroll ticks: positive=up, negative=down"},
            "x": {"type": "integer"}, "y": {"type": "integer"},
        }, "required": ["amount"]},
        "action_drag": {"type": "object", "properties": {
            "start_x": {"type": "integer"}, "start_y": {"type": "integer"},
            "end_x": {"type": "integer"}, "end_y": {"type": "integer"},
            "duration": {"type": "number"},
        }, "required": ["start_x", "start_y", "end_x", "end_y"]},
        "action_move_mouse": {"type": "object", "properties": {
            "x": {"type": "integer"}, "y": {"type": "integer"},
        }, "required": ["x", "y"]},
        "action_activate_window": {"type": "object", "properties": {
            "app": {"type": "string", "description": "Application name"},
        }, "required": ["app"]},
        "action_clipboard_copy": {"type": "object", "properties": {
            "text": {"type": "string"},
        }, "required": ["text"]},
        "action_clipboard_paste": {"type": "object", "properties": {}},
        "system_check_permissions": {"type": "object", "properties": {}},
        "system_get_mouse_position": {"type": "object", "properties": {}},
        "system_get_screen_size": {"type": "object", "properties": {}},
    }

    TOOL_DESCRIPTIONS = {
        "vision_list_windows": "List all visible windows on screen (app, title, size, window_id)",
        "vision_get_state": "Get current screen state: all windows + OCR text of active window",
        "vision_read_window": "Read text in a window via OCR — returns text with bounding box coordinates for clicking",
        "vision_screenshot": "Capture screenshot of a window or full screen as base64 PNG",
        "vision_get_changes": "Get recent screen changes",
        "action_click": "Click at screen coordinates",
        "action_double_click": "Double click at screen coordinates",
        "action_right_click": "Right click at screen coordinates",
        "action_type_text": "Type text at current cursor position",
        "action_press": "Press a keyboard key (enter, tab, escape, space, up, down, etc.)",
        "action_hotkey": 'Keyboard shortcut — e.g. ["cmd","c"] for copy, ["cmd","tab"] for app switch',
        "action_scroll": "Scroll: positive=up, negative=down",
        "action_drag": "Drag from (start_x, start_y) to (end_x, end_y)",
        "action_move_mouse": "Move mouse cursor to coordinates without clicking",
        "action_activate_window": "Bring an application window to the front",
        "action_clipboard_copy": "Copy text to clipboard",
        "action_clipboard_paste": "Get text from clipboard",
        "system_check_permissions": "Check if accessibility permissions are granted for mouse/keyboard control",
        "system_get_mouse_position": "Get current mouse cursor coordinates",
        "system_get_screen_size": "Get screen dimensions in pixels",
    }

    @server.list_tools()
    async def list_tools():
        return [
            Tool(name=name, description=TOOL_DESCRIPTIONS[name], inputSchema=TOOL_SCHEMAS[name])
            for name in tools.keys()
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        handler = tools.get(name)
        if handler is None:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
        try:
            result = await handler(**arguments)
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, default=str))]
        except Exception as e:
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    print(f"vision-pipe v2: {len(tools)} tools ready (vision + action + system)", file=sys.stderr)
    async with stdio_server() as (read, write):
        init_options = server.create_initialization_options()
        init_options.instructions = MCP_INSTRUCTIONS
        await server.run(read, write, init_options)
```

- [ ] **Step 3: Install updated deps and run all tests**

Run:
```bash
cd /Users/transoff/Desktop/vision_pipeline
.venv/bin/pip install -e ".[dev]"
.venv/bin/python -m pytest tests/ -v
```

Expected: All tests PASS (old + new)

- [ ] **Step 4: Test via mcporter**

Run:
```bash
source ~/.nvm/nvm.sh && nvm use 22
mcporter list --config /tmp/mcp-vision.json
mcporter call vision-pipe vision_list_windows --config /tmp/mcp-vision.json
mcporter call vision-pipe system_get_screen_size --config /tmp/mcp-vision.json
```

Expected: vision-pipe shows 20 tools, list_windows returns windows, screen_size returns dimensions

- [ ] **Step 5: Commit**

```bash
git add src/vision_pipe/cli.py pyproject.toml
git commit -m "feat: CLI v2 — 20 MCP tools with instructions, actions as core dependency"
```
