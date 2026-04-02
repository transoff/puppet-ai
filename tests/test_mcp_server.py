import pytest
from vision_pipe.server.mcp import create_vision_tools, VisionMCPContext
from vision_pipe.core.world_model import WorldModel
from vision_pipe.types import Bounds, FocusPriority, FocusResult, RegionInfo, ScanResult


class MockPeripheral:
    async def scan(self, image_bytes):
        return ScanResult(summary="Test screen", regions=[RegionInfo(name="main", bounds=Bounds(x=0, y=0, w=800, h=600), description="Main content")])


class MockFoveal:
    async def focus(self, image_bytes, region, context):
        return FocusResult(region_name=region.name, description=f"Detailed: {context}", extracted_data={"mock": True})


class MockCapture:
    async def capture_bytes(self):
        from PIL import Image
        import io
        img = Image.new("RGB", (800, 600), (255, 255, 255))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    async def capture(self):
        import numpy as np
        return np.full((600, 800, 3), 255, dtype=np.uint8)


@pytest.fixture
def ctx():
    return VisionMCPContext(world_model=WorldModel(), peripheral=MockPeripheral(), foveal=MockFoveal(), capture=MockCapture())


@pytest.mark.asyncio
async def test_get_state_empty(ctx):
    tools = create_vision_tools(ctx)
    result = await tools["get_state"]()
    assert "summary" in result


@pytest.mark.asyncio
async def test_describe_triggers_scan_and_focus(ctx):
    tools = create_vision_tools(ctx)
    result = await tools["describe"](region="main")
    assert "Detailed" in result["description"]


@pytest.mark.asyncio
async def test_describe_full_screen(ctx):
    tools = create_vision_tools(ctx)
    result = await tools["describe"]()
    assert "summary" in result


@pytest.mark.asyncio
async def test_focus_tool(ctx):
    tools = create_vision_tools(ctx)
    await tools["describe"]()
    result = await tools["focus"](region="main", priority="high")
    assert result["status"] == "ok"


@pytest.mark.asyncio
async def test_ignore_tool(ctx):
    tools = create_vision_tools(ctx)
    await tools["describe"]()
    result = await tools["ignore"](region="main")
    assert result["status"] == "ok"


@pytest.mark.asyncio
async def test_get_changes(ctx):
    tools = create_vision_tools(ctx)
    await tools["describe"](region="main")
    result = await tools["get_changes"]()
    assert isinstance(result["changes"], list)
