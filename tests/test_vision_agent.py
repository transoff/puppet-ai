# tests/test_vision_agent.py
import pytest
from puppet_ai.core.vision_agent import VisionAgent, resolve_provider

def test_vision_agent_init_no_config():
    agent = VisionAgent()
    assert agent.provider is None
    assert agent.model is None

def test_resolve_provider_from_env(monkeypatch):
    monkeypatch.setenv("PUPPET_VISION_PROVIDER", "anthropic")
    monkeypatch.setenv("PUPPET_VISION_MODEL", "claude-haiku-4-5-20251001")
    provider, model = resolve_provider()
    assert provider == "anthropic"
    assert model == "claude-haiku-4-5-20251001"

def test_resolve_provider_empty_env(monkeypatch):
    monkeypatch.delenv("PUPPET_VISION_PROVIDER", raising=False)
    monkeypatch.delenv("PUPPET_VISION_MODEL", raising=False)
    provider, model = resolve_provider()
    assert provider is None
    assert model is None

def test_vision_agent_graceful_failure():
    agent = VisionAgent()
    import asyncio
    result = asyncio.run(agent.analyze(b"fake image bytes"))
    assert result == ""
