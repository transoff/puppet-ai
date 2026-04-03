from __future__ import annotations
import time
import pytest
from puppet_ai.core.ocr_cache import OcrCache


@pytest.fixture
def cache():
    return OcrCache(ttl=2.0)


def test_cache_miss(cache):
    assert cache.get(window_id=1, pixel_hash="abc") is None

def test_cache_hit(cache):
    data = {"text": "hello", "elements": []}
    cache.put(window_id=1, pixel_hash="abc", data=data)
    assert cache.get(window_id=1, pixel_hash="abc") == data

def test_cache_expired(cache):
    cache._ttl = 0.1
    cache.put(window_id=1, pixel_hash="abc", data={"text": "hello"})
    time.sleep(0.15)
    assert cache.get(window_id=1, pixel_hash="abc") is None

def test_cache_invalidate(cache):
    cache.put(window_id=1, pixel_hash="abc", data={"text": "hello"})
    cache.invalidate()
    assert cache.get(window_id=1, pixel_hash="abc") is None

def test_cache_different_hash(cache):
    cache.put(window_id=1, pixel_hash="abc", data={"text": "hello"})
    assert cache.get(window_id=1, pixel_hash="def") is None

def test_cache_different_window(cache):
    cache.put(window_id=1, pixel_hash="abc", data={"text": "hello"})
    assert cache.get(window_id=2, pixel_hash="abc") is None
