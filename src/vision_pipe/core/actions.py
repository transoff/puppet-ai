from __future__ import annotations
import subprocess
import pyautogui
import pyperclip


class DesktopActions:
    def __init__(self, failsafe: bool = True) -> None:
        pyautogui.FAILSAFE = failsafe
        self._pag = pyautogui

    def click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> dict:
        self._pag.click(x, y, button=button, clicks=clicks)
        return {"status": "ok", "action": "click", "x": x, "y": y, "button": button}

    def double_click(self, x: int, y: int) -> dict:
        self._pag.click(x, y, button="left", clicks=2)
        return {"status": "ok", "action": "double_click", "x": x, "y": y}

    def right_click(self, x: int, y: int) -> dict:
        self._pag.click(x, y, button="right", clicks=1)
        return {"status": "ok", "action": "right_click", "x": x, "y": y}

    def type_text(self, text: str, interval: float = 0) -> dict:
        self._pag.write(text, interval=interval)
        return {"status": "ok", "action": "type_text", "length": len(text)}

    def press(self, key: str, presses: int = 1) -> dict:
        self._pag.press(key, presses=presses)
        return {"status": "ok", "action": "press", "key": key}

    def hotkey(self, keys: list[str]) -> dict:
        self._pag.hotkey(*keys)
        return {"status": "ok", "action": "hotkey", "keys": keys}

    def scroll(self, amount: int, x: int | None = None, y: int | None = None) -> dict:
        kwargs = {}
        if x is not None:
            kwargs["x"] = x
        if y is not None:
            kwargs["y"] = y
        self._pag.scroll(amount, **kwargs)
        return {"status": "ok", "action": "scroll", "amount": amount}

    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.5) -> dict:
        self._pag.moveTo(start_x, start_y)
        self._pag.drag(end_x - start_x, end_y - start_y, duration=duration, button="left")
        return {"status": "ok", "action": "drag", "from": [start_x, start_y], "to": [end_x, end_y]}

    def move_mouse(self, x: int, y: int, duration: float = 0) -> dict:
        self._pag.moveTo(x, y, duration=duration)
        return {"status": "ok", "action": "move_mouse", "x": x, "y": y}

    def get_mouse_position(self) -> dict:
        x, y = self._pag.position()
        return {"x": x, "y": y}

    def get_screen_size(self) -> dict:
        w, h = self._pag.size()
        return {"width": w, "height": h}

    def activate_window(self, app: str) -> dict:
        result = subprocess.run(
            ["osascript", "-e", f'tell application "{app}" to activate'],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return {"status": "ok", "action": "activate_window", "app": app}
        return {"status": "error", "error": result.stderr.strip()}

    def clipboard_copy(self, text: str) -> dict:
        pyperclip.copy(text)
        return {"status": "ok", "action": "clipboard_copy"}

    def clipboard_paste(self) -> dict:
        text = pyperclip.paste()
        return {"status": "ok", "action": "clipboard_paste", "text": text}
