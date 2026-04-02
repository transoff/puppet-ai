from __future__ import annotations
from vision_pipe.config.schema import CaptureConfig, PhaseConfig, VisionPipeConfig

_PRESETS = {
    "fast": VisionPipeConfig(
        peripheral=PhaseConfig(provider="ollama/moondream2", resolution="256x256"),
        foveal=PhaseConfig(provider="sampling", hint="haiku"),
        capture=CaptureConfig(fps=8, diff_threshold=3.0),
    ),
    "balanced": VisionPipeConfig(
        peripheral=PhaseConfig(provider="ollama/moondream2", resolution="512x512"),
        foveal=PhaseConfig(provider="sampling", hint="sonnet"),
        capture=CaptureConfig(fps=4, diff_threshold=5.0),
    ),
    "quality": VisionPipeConfig(
        peripheral=PhaseConfig(provider="gemini-flash", resolution="768x768"),
        foveal=PhaseConfig(provider="gemini-pro"),
        capture=CaptureConfig(fps=2, diff_threshold=2.0),
    ),
}


def get_preset(name: str) -> VisionPipeConfig:
    if name not in _PRESETS:
        raise KeyError(f"Unknown preset: {name}. Available: {list(_PRESETS.keys())}")
    return _PRESETS[name].model_copy(deep=True)


def list_presets() -> list[str]:
    return list(_PRESETS.keys())
