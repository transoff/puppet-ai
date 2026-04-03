from __future__ import annotations
import asyncio
import time
import numpy as np


class ScreenStabilizer:
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
    stabilizer = ScreenStabilizer(threshold=threshold, stable_count=stable_count)
    start = time.perf_counter()
    while time.perf_counter() - start < timeout:
        frame = await capture_fn()
        if stabilizer.is_stable(frame):
            return time.perf_counter() - start, True
        await asyncio.sleep(poll_interval)
    return time.perf_counter() - start, False
