# src/puppet_ai/core/world_model.py
from __future__ import annotations

from datetime import datetime, timezone

from puppet_ai.types import (
    ChangeEvent,
    FocusPriority,
    FocusResult,
    RegionInfo,
    ScanResult,
    WorldState,
)


class WorldModel:
    def __init__(self, history_limit: int = 100) -> None:
        self._summary: str = ""
        self._regions: dict[str, RegionInfo] = {}
        self._history: list[ChangeEvent] = []
        self._history_limit = history_limit

    def get_state(self) -> WorldState:
        return WorldState(
            summary=self._summary,
            regions=list(self._regions.values()),
            history=list(self._history),
        )

    def update_from_scan(self, scan: ScanResult) -> None:
        self._summary = scan.summary
        focus_map = {name: r.focus for name, r in self._regions.items()}
        self._regions.clear()
        now = datetime.now(timezone.utc)
        for region in scan.regions:
            region.focus = focus_map.get(region.name, FocusPriority.NORMAL)
            region.last_change = now
            self._regions[region.name] = region

    def update_from_focus(self, focus: FocusResult) -> None:
        now = datetime.now(timezone.utc)
        if focus.region_name in self._regions:
            region = self._regions[focus.region_name]
            region.description = focus.description
            region.last_change = now
        self._add_history(
            ChangeEvent(
                time=now,
                delta=f"{focus.region_name}: {focus.description}",
                region_name=focus.region_name,
            )
        )

    def set_focus(self, region_name: str, priority: FocusPriority) -> None:
        if region_name in self._regions:
            self._regions[region_name].focus = priority

    def find_region(self, name: str) -> RegionInfo | None:
        return self._regions.get(name)

    def get_changes(self, since: datetime | None = None) -> list[ChangeEvent]:
        if since is None:
            return list(self._history)
        return [e for e in self._history if e.time >= since]

    def _add_history(self, event: ChangeEvent) -> None:
        self._history.insert(0, event)
        if len(self._history) > self._history_limit:
            self._history = self._history[: self._history_limit]
