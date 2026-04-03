# src/puppet_ai/providers/base.py
from __future__ import annotations
from typing import Protocol, runtime_checkable
from puppet_ai.types import FocusResult, RegionInfo, ScanResult

@runtime_checkable
class VisionProvider(Protocol):
    async def scan(self, image: bytes) -> ScanResult: ...
    async def focus(self, image: bytes, region: RegionInfo, context: str) -> FocusResult: ...
