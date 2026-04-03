"""Example: Read what's on screen right now."""
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

    # List all open windows
    windows = await tools["vision_list_windows"]()
    print("Open windows:")
    for w in windows:
        print(f"  {w['app']:20s} — {w['title'][:50]}")

    # Read text from the frontmost window
    state = await tools["vision_read_window"]()
    print(f"\nActive window: {state.get('app')} ({state.get('size')})")
    print(f"Text preview:\n{state.get('text', '')[:500]}")


if __name__ == "__main__":
    asyncio.run(main())
