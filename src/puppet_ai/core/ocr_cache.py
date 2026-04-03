# src/puppet_ai/core/ocr_cache.py
from __future__ import annotations
import hashlib
import time
from dataclasses import dataclass


@dataclass
class CacheEntry:
    window_id: int
    pixel_hash: str
    data: dict
    timestamp: float


class OcrCache:
    def __init__(self, ttl: float = 2.0) -> None:
        self._ttl = ttl
        self._entries: dict[int, CacheEntry] = {}

    def get(self, window_id: int, pixel_hash: str) -> dict | None:
        entry = self._entries.get(window_id)
        if entry is None:
            return None
        if entry.pixel_hash != pixel_hash:
            return None
        if time.time() - entry.timestamp > self._ttl:
            del self._entries[window_id]
            return None
        return entry.data

    def put(self, window_id: int, pixel_hash: str, data: dict) -> None:
        self._entries[window_id] = CacheEntry(window_id=window_id, pixel_hash=pixel_hash, data=data, timestamp=time.time())

    def invalidate(self) -> None:
        self._entries.clear()

    @staticmethod
    def compute_pixel_hash(image_bytes: bytes) -> str:
        return hashlib.md5(image_bytes[:4096]).hexdigest()
