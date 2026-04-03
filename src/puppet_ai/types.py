# src/puppet_ai/types.py
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class FocusPriority(str, Enum):
    HIGH = "high"
    NORMAL = "normal"
    IGNORED = "ignored"


class Bounds(BaseModel):
    x: int
    y: int
    w: int
    h: int


class RegionInfo(BaseModel):
    name: str
    bounds: Bounds
    description: str = ""
    focus: FocusPriority = FocusPriority.NORMAL
    last_change: datetime | None = None


class ScanResult(BaseModel):
    """Output of Phase 1 (peripheral vision)."""
    summary: str
    regions: list[RegionInfo]


class FocusResult(BaseModel):
    """Output of Phase 2 (foveal focus)."""
    region_name: str
    description: str
    extracted_data: dict[str, Any] = Field(default_factory=dict)


class ChangeEvent(BaseModel):
    time: datetime
    delta: str
    region_name: str | None = None


class WorldState(BaseModel):
    """The complete world model returned to agents."""
    summary: str
    regions: list[RegionInfo] = Field(default_factory=list)
    history: list[ChangeEvent] = Field(default_factory=list)


class ChangedArea(BaseModel):
    """Output of pixel diff detector."""
    bounds: Bounds
    diff_percentage: float
