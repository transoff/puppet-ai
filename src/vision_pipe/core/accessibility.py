# src/vision_pipe/core/accessibility.py
"""macOS Accessibility API — get UI element tree from any application."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class UIElement:
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


def get_ui_elements(app_name: str, role_filter: str | None = None, max_depth: int = 5, max_elements: int = 200) -> list[UIElement]:
    try:
        import AppKit
        import ApplicationServices as AS
    except ImportError:
        return []

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
    _walk_element(app_ref, elements, role_filter, max_depth, max_elements, 0)
    return elements


def _walk_element(element, results, role_filter, max_depth, max_elements, depth):
    import ApplicationServices as AS

    if depth > max_depth or len(results) >= max_elements:
        return

    err, role = AS.AXUIElementCopyAttributeValue(element, "AXRole", None)
    if err != 0:
        return
    role = str(role) if role else ""

    if role_filter and role != role_filter:
        err, children = AS.AXUIElementCopyAttributeValue(element, "AXChildren", None)
        if err == 0 and children:
            for child in children:
                _walk_element(child, results, role_filter, max_depth, max_elements, depth + 1)
        return

    err, title = AS.AXUIElementCopyAttributeValue(element, "AXTitle", None)
    title = str(title) if err == 0 and title else ""

    err, value = AS.AXUIElementCopyAttributeValue(element, "AXValue", None)
    value = str(value) if err == 0 and value else ""

    err, pos_ref = AS.AXUIElementCopyAttributeValue(element, "AXPosition", None)
    err2, size_ref = AS.AXUIElementCopyAttributeValue(element, "AXSize", None)

    if err == 0 and err2 == 0 and pos_ref and size_ref:
        try:
            success, pos = AS.AXValueGetValue(pos_ref, AS.kAXValueTypeCGPoint, None)
            success2, size = AS.AXValueGetValue(size_ref, AS.kAXValueTypeCGSize, None)
            if success and success2:
                x, y = int(pos.x), int(pos.y)
                w, h = int(size.width), int(size.height)
                if w > 2 and h > 2 and (title or value or role in ("AXButton", "AXCheckBox", "AXLink", "AXTextField", "AXTextArea", "AXMenuItem")):
                    results.append(UIElement(role=role, title=title, value=value, x=x, y=y, w=w, h=h))
        except Exception:
            pass

    err, children = AS.AXUIElementCopyAttributeValue(element, "AXChildren", None)
    if err == 0 and children:
        for child in children:
            _walk_element(child, results, role_filter, max_depth, max_elements, depth + 1)
