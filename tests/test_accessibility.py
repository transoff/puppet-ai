# tests/test_accessibility.py
from __future__ import annotations
import pytest
from puppet_ai.core.accessibility import get_ui_elements, UIElement


def test_get_ui_elements_returns_list():
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
