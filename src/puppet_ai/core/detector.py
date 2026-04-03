# src/puppet_ai/core/detector.py
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from puppet_ai.types import Bounds, ChangedArea


@dataclass
class DetectionResult:
    has_change: bool
    overall_diff: float = 0.0
    changed_areas: list[ChangedArea] = field(default_factory=list)


class ChangeDetector:
    """Pixel-diff change detector. Compares frames and finds changed regions."""

    def __init__(self, diff_threshold: float = 5.0, grid_size: int = 8):
        self._threshold = diff_threshold
        self._grid_size = grid_size
        self._prev_frame: np.ndarray | None = None

    def update(self, frame: np.ndarray) -> DetectionResult:
        """Compare frame against previous. Returns detection result."""
        if self._prev_frame is None:
            self._prev_frame = frame.copy()
            return DetectionResult(
                has_change=True,
                overall_diff=100.0,
                changed_areas=[
                    ChangedArea(
                        bounds=Bounds(x=0, y=0, w=frame.shape[1], h=frame.shape[0]),
                        diff_percentage=100.0,
                    )
                ],
            )

        diff = np.abs(frame.astype(np.int16) - self._prev_frame.astype(np.int16))
        overall_diff = (diff.sum() / (frame.size * 255)) * 100

        changed_areas = self._find_changed_areas(diff, frame.shape)

        if not changed_areas:
            return DetectionResult(has_change=False, overall_diff=overall_diff)

        self._prev_frame = frame.copy()

        return DetectionResult(
            has_change=True,
            overall_diff=overall_diff,
            changed_areas=changed_areas,
        )

    def _find_changed_areas(
        self, diff: np.ndarray, shape: tuple[int, ...]
    ) -> list[ChangedArea]:
        """Split frame into grid cells and find which ones changed."""
        h, w = shape[0], shape[1]
        cell_h = h // self._grid_size
        cell_w = w // self._grid_size
        areas: list[ChangedArea] = []

        for row in range(self._grid_size):
            for col in range(self._grid_size):
                y1 = row * cell_h
                x1 = col * cell_w
                y2 = min(y1 + cell_h, h)
                x2 = min(x1 + cell_w, w)

                cell_diff = diff[y1:y2, x1:x2]
                cell_pct = (cell_diff.sum() / (cell_diff.size * 255)) * 100

                if cell_pct > self._threshold:
                    areas.append(
                        ChangedArea(
                            bounds=Bounds(x=x1, y=y1, w=x2 - x1, h=y2 - y1),
                            diff_percentage=cell_pct,
                        )
                    )

        return areas
