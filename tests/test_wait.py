from __future__ import annotations
import pytest
import numpy as np
from puppet_ai.core.wait import ScreenStabilizer


def test_stabilizer_identical_frames():
    s = ScreenStabilizer(threshold=5.0, stable_count=2)
    frame = np.full((100, 100, 3), 128, dtype=np.uint8)
    assert s.is_stable(frame) is False  # first frame
    assert s.is_stable(frame) is True   # second identical = stable


def test_stabilizer_changing_frames():
    s = ScreenStabilizer(threshold=5.0, stable_count=2)
    frame1 = np.full((100, 100, 3), 128, dtype=np.uint8)
    frame2 = np.full((100, 100, 3), 0, dtype=np.uint8)
    assert s.is_stable(frame1) is False
    assert s.is_stable(frame2) is False


def test_stabilizer_eventual_stability():
    s = ScreenStabilizer(threshold=5.0, stable_count=2)
    frame1 = np.full((100, 100, 3), 128, dtype=np.uint8)
    frame2 = np.full((100, 100, 3), 0, dtype=np.uint8)
    s.is_stable(frame1)
    s.is_stable(frame2)
    assert s.is_stable(frame2) is True


def test_stabilizer_reset():
    s = ScreenStabilizer(threshold=5.0, stable_count=2)
    frame = np.full((100, 100, 3), 128, dtype=np.uint8)
    s.is_stable(frame)
    s.is_stable(frame)
    s.reset()
    assert s.is_stable(frame) is False
