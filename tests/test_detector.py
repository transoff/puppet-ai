# tests/test_detector.py
import numpy as np
import pytest

from vision_pipe.core.detector import ChangeDetector


@pytest.fixture
def detector():
    return ChangeDetector(diff_threshold=5.0)


@pytest.fixture
def white_frame():
    return np.full((600, 800, 3), 255, dtype=np.uint8)


@pytest.fixture
def frame_with_red_block():
    frame = np.full((600, 800, 3), 255, dtype=np.uint8)
    frame[0:100, 600:800] = [255, 0, 0]
    return frame


def test_no_change_on_identical_frames(detector, white_frame):
    detector.update(white_frame)
    result = detector.update(white_frame)
    assert result.has_change is False
    assert result.changed_areas == []


def test_detects_change(detector, white_frame, frame_with_red_block):
    detector.update(white_frame)
    result = detector.update(frame_with_red_block)
    assert result.has_change is True
    assert len(result.changed_areas) > 0


def test_first_frame_is_always_change(detector, white_frame):
    result = detector.update(white_frame)
    assert result.has_change is True


def test_overall_diff_percentage(detector, white_frame, frame_with_red_block):
    detector.update(white_frame)
    result = detector.update(frame_with_red_block)
    assert result.overall_diff > 0


def test_below_threshold_no_change(detector, white_frame):
    almost_same = white_frame.copy()
    almost_same[0, 0] = [254, 254, 254]  # tiny change
    detector.update(white_frame)
    result = detector.update(almost_same)
    assert result.has_change is False


def test_changed_area_has_bounds(detector, white_frame, frame_with_red_block):
    detector.update(white_frame)
    result = detector.update(frame_with_red_block)
    assert result.has_change is True
    for area in result.changed_areas:
        assert area.bounds.w > 0
        assert area.bounds.h > 0
