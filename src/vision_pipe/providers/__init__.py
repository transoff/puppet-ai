# src/vision_pipe/providers/__init__.py
from __future__ import annotations
import importlib
import importlib.metadata
import importlib.util
from pathlib import Path
from typing import Any
from vision_pipe.providers.base import VisionProvider

class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, type[VisionProvider]] = {}

    def register(self, name: str, provider_cls: type[VisionProvider]) -> None:
        self._providers[name] = provider_cls

    def get(self, name: str) -> type[VisionProvider]:
        if name not in self._providers:
            raise KeyError(f"Provider not found: {name}")
        return self._providers[name]

    def create(self, name: str, **kwargs: Any) -> VisionProvider:
        cls = self.get(name)
        return cls(**kwargs)

    def list(self) -> list[str]:
        return list(self._providers.keys())

    def discover_entry_points(self) -> None:
        try:
            eps = importlib.metadata.entry_points(group="vision_pipe.providers")
        except TypeError:
            eps = importlib.metadata.entry_points().get("vision_pipe.providers", [])
        for ep in eps:
            self._providers[ep.name] = ep.load()

    def load_custom(self, path: str) -> type[VisionProvider]:
        file_path = Path(path)
        spec = importlib.util.spec_from_file_location("custom_provider", file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load provider from {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and attr is not VisionProvider and issubclass(attr, VisionProvider):
                return attr
        raise ImportError(f"No VisionProvider subclass found in {path}")
