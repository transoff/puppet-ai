import pytest

from puppet_ai.providers import ProviderRegistry
from puppet_ai.providers.base import VisionProvider
from puppet_ai.types import FocusResult, RegionInfo, ScanResult


class FakeProvider(VisionProvider):
    async def scan(self, image: bytes) -> ScanResult:
        return ScanResult(summary="fake", regions=[])

    async def focus(self, image: bytes, region: RegionInfo, context: str) -> FocusResult:
        return FocusResult(region_name=region.name, description="fake focus")


def test_register_and_get_provider():
    registry = ProviderRegistry()
    registry.register("fake", FakeProvider)
    assert registry.get("fake") is FakeProvider


def test_get_unknown_provider_raises():
    registry = ProviderRegistry()
    with pytest.raises(KeyError, match="unknown"):
        registry.get("unknown")


def test_list_registered_providers():
    registry = ProviderRegistry()
    registry.register("a", FakeProvider)
    registry.register("b", FakeProvider)
    names = registry.list()
    assert "a" in names
    assert "b" in names


def test_register_duplicate_overwrites():
    registry = ProviderRegistry()
    registry.register("fake", FakeProvider)
    registry.register("fake", FakeProvider)
    assert registry.get("fake") is FakeProvider


def test_create_instance():
    registry = ProviderRegistry()
    registry.register("fake", FakeProvider)
    instance = registry.create("fake")
    assert isinstance(instance, FakeProvider)
