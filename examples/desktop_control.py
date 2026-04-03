"""Example: Control desktop apps — Finder, Spotlight, clipboard."""
import asyncio
from puppet_ai.core.capture import ScreenCapture
from puppet_ai.core.actions import DesktopActions
from puppet_ai.server.mcp import VisionPipeContext, create_all_tools


async def main():
    ctx = VisionPipeContext(
        capture=ScreenCapture(),
        actions=DesktopActions(failsafe=True),
    )
    tools = create_all_tools(ctx)

    # Activate Finder
    await tools["action_activate_window"](app="Finder")
    await asyncio.sleep(0.5)

    # Get UI elements (buttons, links, text fields)
    ui = await tools["vision_ui_elements"](app="Finder")
    print(f"Finder UI elements: {ui.get('count', 0)}")
    for el in ui.get("elements", [])[:10]:
        print(f"  [{el['role']}] {el.get('title', '')}")

    # Use clipboard to type text safely (works with any keyboard layout)
    await tools["action_clipboard_copy"](text="Hello from puppet-ai!")
    clipboard = await tools["action_clipboard_paste"]()
    print(f"\nClipboard: {clipboard.get('text')}")

    # Get screen info
    screen = await tools["system_get_screen_size"]()
    mouse = await tools["system_get_mouse_position"]()
    print(f"\nScreen: {screen['width']}x{screen['height']}")
    print(f"Mouse: ({mouse['x']}, {mouse['y']})")


if __name__ == "__main__":
    asyncio.run(main())
