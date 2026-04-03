"""Example: Open a website in Safari and read its content."""
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

    # Open a URL in Safari
    result = await tools["action_open_url"](
        url="https://example.com", browser="Safari"
    )
    print(f"Opened URL: {result.get('url')}")

    # Read the page content via OCR
    page = await tools["vision_read_window"](app="Safari")
    print(f"\nPage text:\n{page.get('text', '')[:1000]}")

    # Click a link by its text
    click = await tools["action_click_text"](text="More information", app="Safari")
    if click.get("status") == "ok":
        print(f"\nClicked '{click['clicked']}' at ({click['x']}, {click['y']})")

    # Scroll down
    await tools["action_scroll"](amount=-3, app="Safari")

    # Read again after scrolling
    page2 = await tools["vision_read_window"](app="Safari")
    print(f"\nAfter scroll:\n{page2.get('text', '')[:500]}")


if __name__ == "__main__":
    asyncio.run(main())
