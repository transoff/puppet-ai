from datetime import datetime, timezone

from vision_pipe.types import (
    Bounds,
    ChangeEvent,
    ChangedArea,
    FocusPriority,
    FocusResult,
    RegionInfo,
    ScanResult,
    WorldState,
)


def test_bounds_creation():
    b = Bounds(x=10, y=20, w=100, h=200)
    assert b.x == 10
    assert b.w == 100


def test_region_info_defaults():
    r = RegionInfo(name="header", bounds=Bounds(x=0, y=0, w=800, h=60))
    assert r.description == ""
    assert r.focus == FocusPriority.NORMAL
    assert r.last_change is None


def test_scan_result_with_regions():
    result = ScanResult(
        summary="VS Code editor",
        regions=[
            RegionInfo(name="editor", bounds=Bounds(x=0, y=0, w=800, h=600)),
        ],
    )
    assert len(result.regions) == 1
    assert result.regions[0].name == "editor"


def test_focus_result_extracted_data():
    result = FocusResult(
        region_name="content",
        description="Temperature: 23°C",
        extracted_data={"temperature": 23},
    )
    assert result.extracted_data["temperature"] == 23


def test_world_state_serialization():
    now = datetime.now(timezone.utc)
    state = WorldState(
        summary="Browser open",
        regions=[
            RegionInfo(
                name="main",
                bounds=Bounds(x=0, y=0, w=800, h=600),
                description="Weather page",
                last_change=now,
            ),
        ],
        history=[ChangeEvent(time=now, delta="Page loaded", region_name="main")],
    )
    data = state.model_dump()
    restored = WorldState.model_validate(data)
    assert restored.summary == "Browser open"
    assert len(restored.history) == 1


def test_changed_area():
    area = ChangedArea(bounds=Bounds(x=600, y=0, w=200, h=100), diff_percentage=15.3)
    assert area.diff_percentage == 15.3


def test_focus_result_empty_extracted_data():
    result = FocusResult(region_name="sidebar", description="Ads")
    assert result.extracted_data == {}
