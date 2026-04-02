# vision-pipe v3: Performance + Accessibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add macOS Accessibility API for precise UI element targeting, OCR caching for 5x speedup, and smart click-and-wait that eliminates sleep().

**Architecture:** New `accessibility.py` module wraps AXUIElement for UI tree extraction. OCR cache stores results per window with pixel-diff invalidation. `action_click_and_wait` combines click + pixel-diff polling + OCR into one atomic operation.

**Tech Stack:** pyobjc-framework-ApplicationServices (AXUIElement), existing numpy (pixel diff), existing Vision framework (OCR fast/accurate modes)

**Spec:** `docs/superpowers/specs/2026-04-02-vision-pipe-v3-perf-design.md`

---

## File Structure

```
src/vision_pipe/core/
├── accessibility.py    # CREATE: AXUIElement wrapper — get_ui_elements()
├── ocr.py              # MODIFY: add mode="fast"|"accurate" parameter
├── ocr_cache.py        # CREATE: OCR result cache with pixel-diff invalidation
└── wait.py             # CREATE: wait_for_stable() — pixel diff polling

src/vision_pipe/server/
└── mcp.py              # MODIFY: add vision_ui_elements, action_click_and_wait, integrate cache

src/vision_pipe/
├── cli.py              # MODIFY: register new tools
└── instructions.py     # MODIFY: add accessibility + speed tips

tests/
├── test_accessibility.py  # CREATE
├── test_ocr_cache.py      # CREATE
├── test_wait.py           # CREATE
└── test_mcp_v3.py         # CREATE
```

---

### Task 1: Accessibility API Module

**Files:**
- Create: `src/vision_pipe/core/accessibility.py`
- Create: `tests/test_accessibility.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_accessibility.py
from __future__ import annotations
import pytest
from vision_pipe.core.accessibility import get_ui_elements, UIElement


def test_get_ui_elements_returns_list():
    """Test against a real app (Finder is always running)."""
    elements = get_ui_elements("Finder")
    assert isinstance(elements, list)


def test_ui_element_has_required_fields():
    elements = get_ui_elements("Finder")
    if elements:
        e = elements[0]
        assert isinstance(e, UIElement)
        assert hasattr(e, "role")
        assert hasattr(e, "title")
        assert hasattr(e, "x")
        assert hasattr(e, "y")
        assert hasattr(e, "w")
        assert hasattr(e, "h")


def test_ui_element_to_dict():
    elements = get_ui_elements("Finder")
    if elements:
        d = elements[0].to_dict()
        assert "role" in d
        assert "title" in d
        assert "x" in d


def test_unknown_app_returns_empty():
    elements = get_ui_elements("ThisAppDoesNotExist12345")
    assert elements == []


def test_role_filter():
    elements = get_ui_elements("Finder", role_filter="AXButton")
    for e in elements:
        assert e.role == "AXButton"


def test_ui_element_center():
    elements = get_ui_elements("Finder")
    if elements:
        e = elements[0]
        cx, cy = e.center()
        assert cx == e.x + e.w // 2
        assert cy == e.y + e.h // 2
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/test_accessibility.py -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement accessibility module**

```python
# src/vision_pipe/core/accessibility.py
"""macOS Accessibility API — get UI element tree from any application.

Uses AXUIElement to enumerate buttons, checkboxes, text fields, links, etc.
Same API that VoiceOver uses. Requires Accessibility permissions.
"""
from __future__ import annotations

from dataclasses import dataclass

from vision_pipe.core.ocr import _get_retina_scale


@dataclass
class UIElement:
    """A UI element with role, title, value, and screen coordinates."""
    role: str
    title: str
    value: str
    x: int
    y: int
    w: int
    h: int

    def center(self) -> tuple[int, int]:
        return self.x + self.w // 2, self.y + self.h // 2

    def to_dict(self) -> dict:
        d = {"role": self.role, "title": self.title, "x": self.x, "y": self.y, "w": self.w, "h": self.h}
        if self.value:
            d["value"] = self.value
        return d


def get_ui_elements(
    app_name: str,
    role_filter: str | None = None,
    max_depth: int = 5,
    max_elements: int = 200,
) -> list[UIElement]:
    """Get UI elements from an application via macOS Accessibility API.

    Args:
        app_name: Application name (e.g. "Safari", "Chrome", "Finder")
        role_filter: Only return elements with this role (e.g. "AXButton", "AXCheckBox", "AXLink")
        max_depth: Maximum tree traversal depth
        max_elements: Maximum elements to return

    Returns:
        List of UIElement with screen coordinates (logical pixels, ready for pyautogui).
    """
    try:
        import AppKit
        import ApplicationServices as AS
    except ImportError:
        return []

    scale = _get_retina_scale()

    # Find the running application
    workspace = AppKit.NSWorkspace.sharedWorkspace()
    running_apps = workspace.runningApplications()
    target_app = None
    app_lower = app_name.lower()
    for ra in running_apps:
        name = ra.localizedName()
        if name and app_lower in name.lower():
            target_app = ra
            break

    if target_app is None:
        return []

    pid = target_app.processIdentifier()
    app_ref = AS.AXUIElementCreateApplication(pid)

    elements: list[UIElement] = []
    _walk_element(app_ref, elements, role_filter, max_depth, max_elements, scale, 0)
    return elements


def _walk_element(
    element,
    results: list[UIElement],
    role_filter: str | None,
    max_depth: int,
    max_elements: int,
    scale: float,
    depth: int,
) -> None:
    """Recursively walk the accessibility tree."""
    import ApplicationServices as AS

    if depth > max_depth or len(results) >= max_elements:
        return

    # Get role
    err, role = AS.AXUIElementCopyAttributeValue(element, "AXRole", None)
    if err != 0:
        return
    role = str(role) if role else ""

    # Apply filter
    if role_filter and role != role_filter:
        # Still recurse into children
        err, children = AS.AXUIElementCopyAttributeValue(element, "AXChildren", None)
        if err == 0 and children:
            for child in children:
                _walk_element(child, results, role_filter, max_depth, max_elements, scale, depth + 1)
        return

    # Get title
    err, title = AS.AXUIElementCopyAttributeValue(element, "AXTitle", None)
    title = str(title) if err == 0 and title else ""

    # Get value
    err, value = AS.AXUIElementCopyAttributeValue(element, "AXValue", None)
    value = str(value) if err == 0 and value else ""

    # Get position and size
    err, pos_ref = AS.AXUIElementCopyAttributeValue(element, "AXPosition", None)
    err2, size_ref = AS.AXUIElementCopyAttributeValue(element, "AXSize", None)

    if err == 0 and err2 == 0 and pos_ref and size_ref:
        import CoreGraphics as CG
        success, pos = CG.AXValueGetValue(pos_ref, CG.kAXValueTypeCGPoint, None)
        success2, size = CG.AXValueGetValue(size_ref, CG.kAXValueTypeCGSize, None)

        if success and success2:
            # Coordinates from AX API are in logical screen pixels already
            x = int(pos.x)
            y = int(pos.y)
            w = int(size.width)
            h = int(size.height)

            # Only add elements with meaningful size and content
            if w > 2 and h > 2 and (title or value or role in ("AXButton", "AXCheckBox", "AXLink", "AXTextField", "AXTextArea", "AXMenuItem")):
                results.append(UIElement(role=role, title=title, value=value, x=x, y=y, w=w, h=h))

    # Recurse into children
    err, children = AS.AXUIElementCopyAttributeValue(element, "AXChildren", None)
    if err == 0 and children:
        for child in children:
            _walk_element(child, results, role_filter, max_depth, max_elements, scale, depth + 1)
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_accessibility.py -v`
Expected: All 6 tests PASS (or some skip if Finder has no buttons visible)

- [ ] **Step 5: Commit**

```bash
git add src/vision_pipe/core/accessibility.py tests/test_accessibility.py
git commit -m "feat: Accessibility API — get UI elements (buttons, links, checkboxes) from any app"
```

---

### Task 2: OCR Fast Mode + Cache

**Files:**
- Modify: `src/vision_pipe/core/ocr.py`
- Create: `src/vision_pipe/core/ocr_cache.py`
- Create: `tests/test_ocr_cache.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_ocr_cache.py
from __future__ import annotations
import time
import pytest
from vision_pipe.core.ocr_cache import OcrCache


@pytest.fixture
def cache():
    return OcrCache(ttl=2.0)


def test_cache_miss(cache):
    result = cache.get(window_id=1, pixel_hash="abc")
    assert result is None


def test_cache_hit(cache):
    data = {"text": "hello", "elements": []}
    cache.put(window_id=1, pixel_hash="abc", data=data)
    result = cache.get(window_id=1, pixel_hash="abc")
    assert result == data


def test_cache_expired(cache):
    cache._ttl = 0.1
    data = {"text": "hello", "elements": []}
    cache.put(window_id=1, pixel_hash="abc", data=data)
    time.sleep(0.15)
    result = cache.get(window_id=1, pixel_hash="abc")
    assert result is None


def test_cache_invalidate(cache):
    data = {"text": "hello", "elements": []}
    cache.put(window_id=1, pixel_hash="abc", data=data)
    cache.invalidate()
    result = cache.get(window_id=1, pixel_hash="abc")
    assert result is None


def test_cache_different_hash(cache):
    data = {"text": "hello", "elements": []}
    cache.put(window_id=1, pixel_hash="abc", data=data)
    result = cache.get(window_id=1, pixel_hash="def")
    assert result is None


def test_cache_different_window(cache):
    data = {"text": "hello", "elements": []}
    cache.put(window_id=1, pixel_hash="abc", data=data)
    result = cache.get(window_id=2, pixel_hash="abc")
    assert result is None
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/test_ocr_cache.py -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement OCR cache**

```python
# src/vision_pipe/core/ocr_cache.py
"""OCR result cache — avoids re-running OCR when screen hasn't changed."""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field


@dataclass
class CacheEntry:
    window_id: int
    pixel_hash: str
    data: dict
    timestamp: float


class OcrCache:
    """Simple TTL cache for OCR results, keyed by window_id + pixel hash."""

    def __init__(self, ttl: float = 2.0) -> None:
        self._ttl = ttl
        self._entries: dict[int, CacheEntry] = {}

    def get(self, window_id: int, pixel_hash: str) -> dict | None:
        entry = self._entries.get(window_id)
        if entry is None:
            return None
        if entry.pixel_hash != pixel_hash:
            return None
        if time.time() - entry.timestamp > self._ttl:
            del self._entries[window_id]
            return None
        return entry.data

    def put(self, window_id: int, pixel_hash: str, data: dict) -> None:
        self._entries[window_id] = CacheEntry(
            window_id=window_id,
            pixel_hash=pixel_hash,
            data=data,
            timestamp=time.time(),
        )

    def invalidate(self) -> None:
        self._entries.clear()

    @staticmethod
    def compute_pixel_hash(image_bytes: bytes) -> str:
        return hashlib.md5(image_bytes[:4096]).hexdigest()
```

- [ ] **Step 4: Add fast mode to ocr.py**

In `src/vision_pipe/core/ocr.py`, modify `ocr_with_bounds` to accept `mode` parameter:

Change the line:
```python
request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
```

To:
```python
if mode == "fast":
    request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelFast)
else:
    request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
```

And add `mode: str = "accurate"` to the function signature.

- [ ] **Step 5: Run tests**

Run: `.venv/bin/python -m pytest tests/test_ocr_cache.py tests/test_ocr_bounds.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/vision_pipe/core/ocr_cache.py src/vision_pipe/core/ocr.py tests/test_ocr_cache.py
git commit -m "feat: OCR fast mode + result cache with pixel-hash invalidation"
```

---

### Task 3: Wait-for-Stable Module

**Files:**
- Create: `src/vision_pipe/core/wait.py`
- Create: `tests/test_wait.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_wait.py
from __future__ import annotations
import pytest
import numpy as np
from vision_pipe.core.wait import wait_for_stable, ScreenStabilizer


def test_stabilizer_identical_frames():
    """Identical frames = stable immediately."""
    s = ScreenStabilizer(threshold=5.0, stable_count=2)
    frame = np.full((100, 100, 3), 128, dtype=np.uint8)
    assert s.is_stable(frame) is False  # first frame
    assert s.is_stable(frame) is True   # second identical = stable


def test_stabilizer_changing_frames():
    """Different frames = not stable."""
    s = ScreenStabilizer(threshold=5.0, stable_count=2)
    frame1 = np.full((100, 100, 3), 128, dtype=np.uint8)
    frame2 = np.full((100, 100, 3), 0, dtype=np.uint8)
    assert s.is_stable(frame1) is False
    assert s.is_stable(frame2) is False  # different from prev


def test_stabilizer_eventual_stability():
    """After changing, identical frames = stable."""
    s = ScreenStabilizer(threshold=5.0, stable_count=2)
    frame1 = np.full((100, 100, 3), 128, dtype=np.uint8)
    frame2 = np.full((100, 100, 3), 0, dtype=np.uint8)
    s.is_stable(frame1)
    s.is_stable(frame2)
    assert s.is_stable(frame2) is True  # now stable


def test_stabilizer_reset():
    s = ScreenStabilizer(threshold=5.0, stable_count=2)
    frame = np.full((100, 100, 3), 128, dtype=np.uint8)
    s.is_stable(frame)
    s.is_stable(frame)
    s.reset()
    assert s.is_stable(frame) is False  # reset, need to build up again
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/test_wait.py -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement**

```python
# src/vision_pipe/core/wait.py
"""Screen stabilization — wait for screen to stop changing after an action."""
from __future__ import annotations

import asyncio
import time

import numpy as np


class ScreenStabilizer:
    """Detects when the screen has stabilized (stopped changing)."""

    def __init__(self, threshold: float = 3.0, stable_count: int = 3) -> None:
        self._threshold = threshold
        self._stable_count = stable_count
        self._prev_frame: np.ndarray | None = None
        self._consecutive_stable = 0

    def is_stable(self, frame: np.ndarray) -> bool:
        if self._prev_frame is None:
            self._prev_frame = frame.copy()
            self._consecutive_stable = 0
            return False

        diff = np.abs(frame.astype(np.int16) - self._prev_frame.astype(np.int16))
        pct = (diff.sum() / (frame.size * 255)) * 100
        self._prev_frame = frame.copy()

        if pct < self._threshold:
            self._consecutive_stable += 1
        else:
            self._consecutive_stable = 0

        return self._consecutive_stable >= self._stable_count - 1

    def reset(self) -> None:
        self._prev_frame = None
        self._consecutive_stable = 0


async def wait_for_stable(
    capture_fn,
    timeout: float = 5.0,
    poll_interval: float = 0.2,
    threshold: float = 3.0,
    stable_count: int = 3,
) -> tuple[float, bool]:
    """Wait for screen to stabilize after an action.

    Args:
        capture_fn: async callable that returns np.ndarray frame
        timeout: max seconds to wait
        poll_interval: seconds between checks
        threshold: pixel diff threshold for "same frame"
        stable_count: consecutive stable frames needed

    Returns:
        (seconds_waited, did_stabilize)
    """
    stabilizer = ScreenStabilizer(threshold=threshold, stable_count=stable_count)
    start = time.perf_counter()

    while time.perf_counter() - start < timeout:
        frame = await capture_fn()
        if stabilizer.is_stable(frame):
            return time.perf_counter() - start, True
        await asyncio.sleep(poll_interval)

    return time.perf_counter() - start, False
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_wait.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/vision_pipe/core/wait.py tests/test_wait.py
git commit -m "feat: screen stabilizer — wait for screen to stop changing after actions"
```

---

### Task 4: MCP Integration — New Tools + Cache + Instructions

**Files:**
- Modify: `src/vision_pipe/server/mcp.py`
- Modify: `src/vision_pipe/cli.py`
- Modify: `src/vision_pipe/instructions.py`
- Create: `tests/test_mcp_v3.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_mcp_v3.py
from __future__ import annotations
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from vision_pipe.server.mcp import create_all_tools, VisionPipeContext


@pytest.fixture
def ctx():
    cap = MagicMock()
    cap.list_windows.return_value = [
        MagicMock(window_id=1, owner="Safari", title="Google", width=1200, height=800, x=0, y=40),
    ]
    cap.capture_window_bytes = AsyncMock(return_value=b"fake_png")
    cap.capture_bytes = AsyncMock(return_value=b"fake_png")
    cap.capture_window = AsyncMock(return_value=MagicMock())

    act = MagicMock()
    act.click.return_value = {"status": "ok"}
    act.get_mouse_position.return_value = {"x": 100, "y": 200}
    act.get_screen_size.return_value = {"width": 1470, "height": 956}

    return VisionPipeContext(capture=cap, actions=act)


def test_vision_ui_elements_exists(ctx):
    tools = create_all_tools(ctx)
    assert "vision_ui_elements" in tools


def test_action_click_and_wait_exists(ctx):
    tools = create_all_tools(ctx)
    assert "action_click_and_wait" in tools


@pytest.mark.asyncio
async def test_vision_ui_elements_calls_accessibility(ctx):
    tools = create_all_tools(ctx)
    with patch("vision_pipe.server.mcp.get_ui_elements") as mock_ax:
        mock_ax.return_value = []
        result = await tools["vision_ui_elements"](app="Safari")
        mock_ax.assert_called_once()
        assert isinstance(result, dict)
        assert "elements" in result
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/test_mcp_v3.py -v`
Expected: FAIL

- [ ] **Step 3: Add new tools to mcp.py**

Add these imports at the top of `create_all_tools`:

Add `vision_ui_elements` tool:
```python
async def vision_ui_elements(app: str | None = None, role_filter: str | None = None, max_depth: int = 5) -> dict:
    from vision_pipe.core.accessibility import get_ui_elements
    if not app:
        windows = ctx.capture.list_windows()
        if windows:
            app = windows[0].owner
        else:
            return {"error": "No windows found"}
    elements = get_ui_elements(app, role_filter=role_filter, max_depth=max_depth)
    return {"app": app, "elements": [e.to_dict() for e in elements], "count": len(elements)}
```

Add `action_click_and_wait` tool:
```python
async def action_click_and_wait(text: str, app: str | None = None, timeout: float = 5.0) -> dict:
    """Click text and wait for screen to stabilize. Returns new screen state."""
    from vision_pipe.core.accessibility import get_ui_elements
    from vision_pipe.core.ocr import ocr_with_bounds, _get_retina_scale
    from vision_pipe.core.wait import wait_for_stable

    # Find target — try accessibility first, then OCR
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
            elements = ocr_with_bounds(img, window_x=int(win.x / scale), window_y=int(win.y / scale), mode="fast")
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
    await asyncio.sleep(0.3)  # brief pause for action to take effect

    async def capture_frame():
        return await ctx.capture.capture_window(win.window_id)

    waited, stable = await wait_for_stable(capture_frame, timeout=timeout)

    # OCR the new state
    from vision_pipe.core.ocr import ocr_full_text
    try:
        new_img = await ctx.capture.capture_window_bytes(win.window_id)
        new_text = ocr_full_text(new_img)
    except Exception:
        new_text = ""

    # Invalidate cache
    if hasattr(ctx, '_ocr_cache') and ctx._ocr_cache:
        ctx._ocr_cache.invalidate()

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
```

Add both to the returned tools dict.

- [ ] **Step 4: Register tools in cli.py**

Add to TOOL_SCHEMAS:
```python
"vision_ui_elements": {"type": "object", "properties": {"app": {"type": "string"}, "role_filter": {"type": "string", "description": "Filter by role: AXButton, AXCheckBox, AXLink, AXTextField, etc."}, "max_depth": {"type": "integer"}}, },
"action_click_and_wait": {"type": "object", "properties": {"text": {"type": "string", "description": "Text to find and click"}, "app": {"type": "string"}, "timeout": {"type": "number", "description": "Max seconds to wait (default 5)"}}, "required": ["text"]},
```

Add to TOOL_DESCRIPTIONS:
```python
"vision_ui_elements": "Get UI elements (buttons, checkboxes, links, text fields) via Accessibility API — precise clickable targets",
"action_click_and_wait": "Find text, click it, wait for screen to stabilize, return new state — replaces click+sleep+read",
```

- [ ] **Step 5: Update instructions.py**

Add before NAVIGATION STRATEGY:
```
PRECISE CLICKING:
- For UI elements (buttons, checkboxes, links): use vision_ui_elements(app) — gives exact clickable areas with roles
- For text on screen: use action_click_text(text, app) — finds via OCR and clicks center
- BEST: use action_click_and_wait(text, app) — clicks AND waits for result, no sleep() needed
- vision_ui_elements returns roles: AXButton, AXCheckBox, AXLink, AXTextField, AXMenuItem, etc.

SPEED TIPS:
- OCR results are cached — calling vision_read_window twice quickly returns from cache
- Cache is automatically cleared after any action (click, type, scroll)
- action_click_and_wait is faster than click + sleep(3) + read_window — it waits exactly as long as needed
```

- [ ] **Step 6: Run all tests**

Run: `.venv/bin/python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 7: Verify via mcporter**

Run:
```bash
source ~/.nvm/nvm.sh && nvm use 22
mcporter list --config /tmp/mcp-vision.json
mcporter call vision-pipe vision_ui_elements --config /tmp/mcp-vision.json -- Safari
```

Expected: vision-pipe shows 27 tools, ui_elements returns Safari buttons/links

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat: v3 MCP — vision_ui_elements + action_click_and_wait + cache integration"
```
