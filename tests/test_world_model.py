# tests/test_world_model.py
from datetime import datetime, timezone
import pytest
from vision_pipe.core.world_model import WorldModel
from vision_pipe.types import (FocusPriority, FocusResult)


@pytest.fixture
def model():
    return WorldModel(history_limit=50)


def test_empty_state(model):
    state = model.get_state()
    assert state.summary == ""
    assert state.regions == []
    assert state.history == []


def test_update_from_scan(model, sample_scan_result):
    model.update_from_scan(sample_scan_result)
    state = model.get_state()
    assert state.summary == "Browser showing weather.com"
    assert len(state.regions) == 3
    assert state.regions[0].name == "header"


def test_update_from_focus(model, sample_scan_result, sample_focus_result):
    model.update_from_scan(sample_scan_result)
    model.update_from_focus(sample_focus_result)
    state = model.get_state()
    content = next(r for r in state.regions if r.name == "content")
    assert "23°C" in content.description


def test_focus_adds_history_entry(model, sample_scan_result, sample_focus_result):
    model.update_from_scan(sample_scan_result)
    model.update_from_focus(sample_focus_result)
    state = model.get_state()
    assert len(state.history) >= 1
    assert "content" in state.history[0].delta or state.history[0].region_name == "content"


def test_set_focus_priority(model, sample_scan_result):
    model.update_from_scan(sample_scan_result)
    model.set_focus("header", FocusPriority.HIGH)
    state = model.get_state()
    header = next(r for r in state.regions if r.name == "header")
    assert header.focus == FocusPriority.HIGH


def test_set_ignore(model, sample_scan_result):
    model.update_from_scan(sample_scan_result)
    model.set_focus("sidebar", FocusPriority.IGNORED)
    state = model.get_state()
    sidebar = next(r for r in state.regions if r.name == "sidebar")
    assert sidebar.focus == FocusPriority.IGNORED


def test_get_changes_since(model, sample_scan_result, sample_focus_result):
    model.update_from_scan(sample_scan_result)
    before = datetime.now(timezone.utc)
    model.update_from_focus(sample_focus_result)
    changes = model.get_changes(since=before)
    assert len(changes) >= 1


def test_history_limit(model, sample_scan_result):
    model.update_from_scan(sample_scan_result)
    for i in range(60):
        model.update_from_focus(FocusResult(region_name="content", description=f"update {i}"))
    state = model.get_state()
    assert len(state.history) <= 50


def test_find_region_by_name(model, sample_scan_result):
    model.update_from_scan(sample_scan_result)
    region = model.find_region("content")
    assert region is not None
    assert region.name == "content"


def test_find_region_not_found(model):
    assert model.find_region("nonexistent") is None
