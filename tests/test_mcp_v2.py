from __future__ import annotations
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from vision_pipe.server.mcp import create_all_tools, VisionPipeContext


@pytest.fixture
def mock_capture():
    cap = MagicMock()
    cap.list_windows.return_value = [
        MagicMock(window_id=1, owner="Chrome", title="Google", width=1200, height=800),
    ]
    cap.capture_window_bytes = AsyncMock(return_value=b"fake_png")
    cap.capture_bytes = AsyncMock(return_value=b"fake_png")
    return cap


@pytest.fixture
def mock_actions():
    act = MagicMock()
    act.click.return_value = {"status": "ok", "action": "click"}
    act.type_text.return_value = {"status": "ok", "action": "type_text"}
    act.press.return_value = {"status": "ok", "action": "press"}
    act.hotkey.return_value = {"status": "ok", "action": "hotkey"}
    act.scroll.return_value = {"status": "ok", "action": "scroll"}
    act.double_click.return_value = {"status": "ok", "action": "double_click"}
    act.right_click.return_value = {"status": "ok", "action": "right_click"}
    act.drag.return_value = {"status": "ok", "action": "drag"}
    act.move_mouse.return_value = {"status": "ok", "action": "move_mouse"}
    act.activate_window.return_value = {"status": "ok", "action": "activate_window"}
    act.clipboard_copy.return_value = {"status": "ok", "action": "clipboard_copy"}
    act.clipboard_paste.return_value = {"status": "ok", "action": "clipboard_paste", "text": "hello"}
    act.get_mouse_position.return_value = {"x": 100, "y": 200}
    act.get_screen_size.return_value = {"width": 1920, "height": 1080}
    return act


@pytest.fixture
def ctx(mock_capture, mock_actions):
    return VisionPipeContext(capture=mock_capture, actions=mock_actions)


def test_create_all_tools_returns_dict(ctx):
    tools = create_all_tools(ctx)
    assert isinstance(tools, dict)
    assert len(tools) >= 20

def test_vision_tools_present(ctx):
    tools = create_all_tools(ctx)
    assert "vision_list_windows" in tools
    assert "vision_get_state" in tools
    assert "vision_read_window" in tools
    assert "vision_screenshot" in tools

def test_action_tools_present(ctx):
    tools = create_all_tools(ctx)
    for name in ["action_click", "action_type_text", "action_press", "action_hotkey", "action_scroll", "action_drag", "action_activate_window"]:
        assert name in tools

def test_system_tools_present(ctx):
    tools = create_all_tools(ctx)
    assert "system_check_permissions" in tools
    assert "system_get_mouse_position" in tools
    assert "system_get_screen_size" in tools

@pytest.mark.asyncio
async def test_vision_list_windows(ctx):
    tools = create_all_tools(ctx)
    result = await tools["vision_list_windows"]()
    assert len(result) == 1
    assert result[0]["app"] == "Chrome"

@pytest.mark.asyncio
async def test_action_click(ctx):
    tools = create_all_tools(ctx)
    result = await tools["action_click"](x=100, y=200)
    assert result["status"] == "ok"
    ctx.actions.click.assert_called_once_with(100, 200, button="left", clicks=1)

@pytest.mark.asyncio
async def test_action_type_text(ctx):
    tools = create_all_tools(ctx)
    result = await tools["action_type_text"](text="hello")
    assert result["status"] == "ok"

@pytest.mark.asyncio
async def test_action_hotkey(ctx):
    tools = create_all_tools(ctx)
    result = await tools["action_hotkey"](keys=["cmd", "c"])
    assert result["status"] == "ok"

@pytest.mark.asyncio
async def test_system_get_mouse_position(ctx):
    tools = create_all_tools(ctx)
    result = await tools["system_get_mouse_position"]()
    assert result["x"] == 100

@pytest.mark.asyncio
async def test_system_get_screen_size(ctx):
    tools = create_all_tools(ctx)
    result = await tools["system_get_screen_size"]()
    assert result["width"] == 1920

@pytest.mark.asyncio
async def test_vision_screenshot(ctx):
    tools = create_all_tools(ctx)
    with patch("vision_pipe.server.mcp.base64") as mock_b64:
        mock_b64.b64encode.return_value = b"aW1hZ2U="
        # Need to also patch PIL
        with patch("vision_pipe.server.mcp.Image") as mock_pil:
            mock_img = MagicMock()
            mock_img.width = 800
            mock_img.height = 600
            mock_pil.open.return_value = mock_img
            result = await tools["vision_screenshot"](app="Chrome")
            assert "image_base64" in result
