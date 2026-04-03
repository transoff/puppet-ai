import pytest
from puppet_ai.config.schema import VisionPipeConfig, PhaseConfig
from puppet_ai.config.presets import get_preset, list_presets


def test_default_config():
    config = VisionPipeConfig()
    assert config.capture.fps == 4
    assert config.capture.diff_threshold == 5.0
    assert config.peripheral.provider == "ollama/moondream2"
    assert config.foveal.provider == "sampling"


def test_config_from_dict():
    data = {"peripheral": {"provider": "gemini-flash", "resolution": "256x256"}, "foveal": {"provider": "claude-sonnet"}, "capture": {"fps": 10, "diff_threshold": 2.0}}
    config = VisionPipeConfig.model_validate(data)
    assert config.peripheral.provider == "gemini-flash"
    assert config.peripheral.resolution == "256x256"
    assert config.capture.fps == 10


def test_config_from_yaml(tmp_path):
    yaml_content = "peripheral:\n  provider: ollama/llava:7b\n  resolution: 512x512\nfoveal:\n  provider: gemini-flash\ncapture:\n  fps: 8\n  diff_threshold: 3.0\n"
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml_content)
    config = VisionPipeConfig.from_yaml(config_file)
    assert config.peripheral.provider == "ollama/llava:7b"
    assert config.capture.fps == 8


def test_preset_fast():
    config = get_preset("fast")
    assert config.peripheral.resolution == "256x256"


def test_preset_balanced():
    config = get_preset("balanced")
    assert config.peripheral.resolution == "512x512"


def test_preset_quality():
    config = get_preset("quality")
    assert config.peripheral.resolution == "768x768"


def test_list_presets():
    presets = list_presets()
    assert "fast" in presets
    assert "balanced" in presets
    assert "quality" in presets


def test_unknown_preset_raises():
    with pytest.raises(KeyError):
        get_preset("nonexistent")


def test_phase_config_resolution_parsing():
    pc = PhaseConfig(provider="test", resolution="512x512")
    w, h = pc.resolution_tuple()
    assert w == 512 and h == 512


def test_phase_config_hint():
    pc = PhaseConfig(provider="sampling", hint="haiku")
    assert pc.hint == "haiku"
