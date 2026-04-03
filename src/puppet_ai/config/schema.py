from __future__ import annotations
from pathlib import Path
import yaml
from pydantic import BaseModel, Field


class PhaseConfig(BaseModel):
    provider: str = ""
    resolution: str = "512x512"
    hint: str | None = None

    def resolution_tuple(self) -> tuple[int, int]:
        w, h = self.resolution.split("x")
        return int(w), int(h)


class CaptureConfig(BaseModel):
    fps: int = 4
    diff_threshold: float = 5.0


class VisionPipeConfig(BaseModel):
    peripheral: PhaseConfig = Field(default_factory=lambda: PhaseConfig(provider="ollama/moondream2"))
    foveal: PhaseConfig = Field(default_factory=lambda: PhaseConfig(provider="sampling"))
    capture: CaptureConfig = Field(default_factory=CaptureConfig)

    @classmethod
    def from_yaml(cls, path: Path) -> VisionPipeConfig:
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls.model_validate(data)
