from __future__ import annotations
from unittest.mock import MagicMock, patch
import pytest
from vision_pipe.core.actions import DesktopActions


@pytest.fixture
def actions():
    with patch("vision_pipe.core.actions.pyautogui") as mock_pag:
        mock_pag.size.return_value = (1920, 1080)
        mock_pag.position.return_value = (500, 300)
        da = DesktopActions(failsafe=True)
        da._pag = mock_pag
        yield da, mock_pag


def test_click(actions):
    da, mock = actions
    result = da.click(100, 200)
    mock.click.assert_called_once_with(100, 200, button="left", clicks=1)
    assert result["status"] == "ok"

def test_click_right_button(actions):
    da, mock = actions
    da.click(100, 200, button="right")
    mock.click.assert_called_once_with(100, 200, button="right", clicks=1)

def test_double_click(actions):
    da, mock = actions
    da.double_click(300, 400)
    mock.click.assert_called_once_with(300, 400, button="left", clicks=2)

def test_type_text(actions):
    da, mock = actions
    da.type_text("hello")
    mock.write.assert_called_once_with("hello", interval=0)

def test_press_key(actions):
    da, mock = actions
    da.press("enter")
    mock.press.assert_called_once_with("enter", presses=1)

def test_hotkey(actions):
    da, mock = actions
    da.hotkey(["cmd", "c"])
    mock.hotkey.assert_called_once_with("cmd", "c")

def test_scroll(actions):
    da, mock = actions
    da.scroll(-5)
    mock.scroll.assert_called_once_with(-5)

def test_scroll_at_position(actions):
    da, mock = actions
    da.scroll(3, x=100, y=200)
    mock.scroll.assert_called_once_with(3, x=100, y=200)

def test_drag(actions):
    da, mock = actions
    da.drag(100, 200, 300, 400)
    mock.moveTo.assert_called_once_with(100, 200)
    mock.drag.assert_called_once()

def test_move_mouse(actions):
    da, mock = actions
    da.move_mouse(500, 600)
    mock.moveTo.assert_called_once_with(500, 600, duration=0)

def test_get_mouse_position(actions):
    da, mock = actions
    pos = da.get_mouse_position()
    assert pos == {"x": 500, "y": 300}

def test_get_screen_size(actions):
    da, mock = actions
    size = da.get_screen_size()
    assert size == {"width": 1920, "height": 1080}

def test_clipboard_copy(actions):
    da, _ = actions
    with patch("vision_pipe.core.actions.pyperclip") as mock_clip:
        da.clipboard_copy("test")
        mock_clip.copy.assert_called_once_with("test")

def test_clipboard_paste(actions):
    da, _ = actions
    with patch("vision_pipe.core.actions.pyperclip") as mock_clip:
        mock_clip.paste.return_value = "pasted"
        result = da.clipboard_paste()
        assert result["text"] == "pasted"

def test_activate_window(actions):
    da, _ = actions
    with patch("vision_pipe.core.actions.subprocess") as mock_sub:
        mock_sub.run.return_value = MagicMock(returncode=0)
        result = da.activate_window("Chrome")
        assert result["status"] == "ok"
