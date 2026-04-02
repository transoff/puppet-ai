from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from vision_pipe.core.world_model import WorldModel
from vision_pipe.types import FocusPriority


@dataclass
class VisionMCPContext:
    world_model: WorldModel
    peripheral: Any
    foveal: Any
    capture: Any


def create_vision_tools(ctx: VisionMCPContext) -> dict[str, Any]:
    async def get_state() -> dict:
        state = ctx.world_model.get_state()
        return state.model_dump(mode="json")

    async def describe(region: str | None = None) -> dict:
        image_bytes = await ctx.capture.capture_bytes()
        scan_result = await ctx.peripheral.scan(image_bytes)
        ctx.world_model.update_from_scan(scan_result)
        if region is None:
            return ctx.world_model.get_state().model_dump(mode="json")
        region_info = ctx.world_model.find_region(region)
        if region_info is None:
            return {"error": f"Region '{region}' not found"}
        focus_result = await ctx.foveal.focus(image_bytes, region_info, region)
        ctx.world_model.update_from_focus(focus_result)
        return focus_result.model_dump(mode="json")

    async def get_changes(since: str | None = None) -> dict:
        since_dt = None
        if since:
            since_dt = datetime.fromisoformat(since)
        changes = ctx.world_model.get_changes(since=since_dt)
        return {"changes": [c.model_dump(mode="json") for c in changes]}

    async def focus(region: str, priority: str = "high") -> dict:
        try:
            prio = FocusPriority(priority)
        except ValueError:
            return {"error": f"Invalid priority: {priority}"}
        ctx.world_model.set_focus(region, prio)
        return {"status": "ok", "region": region, "priority": priority}

    async def ignore(region: str) -> dict:
        ctx.world_model.set_focus(region, FocusPriority.IGNORED)
        return {"status": "ok", "region": region, "priority": "ignored"}

    async def set_provider(phase: str, provider: str) -> dict:
        if phase not in ("peripheral", "foveal"):
            return {"error": f"Invalid phase: {phase}"}
        ctx.world_model._provider_overrides = getattr(ctx.world_model, "_provider_overrides", {})
        ctx.world_model._provider_overrides[phase] = provider
        return {"status": "ok", "phase": phase, "provider": provider}

    return {
        "get_state": get_state,
        "describe": describe,
        "get_changes": get_changes,
        "focus": focus,
        "ignore": ignore,
        "set_provider": set_provider,
    }
