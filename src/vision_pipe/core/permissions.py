# src/vision_pipe/core/permissions.py
from __future__ import annotations


def check_accessibility() -> dict:
    # Try pyobjc Quartz first (preferred), then ctypes fallback
    try:
        import Quartz
        trusted = Quartz.AXIsProcessTrusted()
        if trusted:
            return {"accessible": True}
        return {
            "accessible": False,
            "instructions": "Accessibility access required for mouse/keyboard control. Go to System Settings → Privacy & Security → Accessibility and add this application (Terminal or your IDE).",
        }
    except AttributeError:
        # AXIsProcessTrusted not exposed via pyobjc Quartz on this platform version;
        # fall back to ctypes against the ApplicationServices framework.
        pass
    except ImportError:
        return {
            "accessible": False,
            "instructions": "pyobjc-framework-Quartz not installed. Run: pip install pyobjc-framework-Quartz",
        }

    try:
        import ctypes
        lib = ctypes.cdll.LoadLibrary(
            "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices"
        )
        lib.AXIsProcessTrusted.restype = ctypes.c_bool
        trusted = lib.AXIsProcessTrusted()
        if trusted:
            return {"accessible": True}
        return {
            "accessible": False,
            "instructions": "Accessibility access required for mouse/keyboard control. Go to System Settings → Privacy & Security → Accessibility and add this application (Terminal or your IDE).",
        }
    except OSError:
        return {
            "accessible": False,
            "instructions": "Could not load ApplicationServices framework. Ensure you are running on macOS.",
        }
