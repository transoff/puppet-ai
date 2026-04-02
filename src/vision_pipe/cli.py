# src/vision_pipe/cli.py
from __future__ import annotations
from pathlib import Path
import click


@click.group()
@click.version_option(package_name="vision-pipe")
def main():
    """vision-pipe: Human-like vision for AI agents."""
    pass


@main.command()
@click.option("--config", type=click.Path(exists=True), help="Path to config YAML")
@click.option("--preset", type=click.Choice(["fast", "balanced", "quality"]), help="Use a built-in preset")
def serve(config: str | None, preset: str | None):
    """Start the MCP server."""
    import asyncio

    from vision_pipe.config.presets import get_preset
    from vision_pipe.config.schema import VisionPipeConfig

    if preset:
        cfg = get_preset(preset)
    elif config:
        cfg = VisionPipeConfig.from_yaml(Path(config))
    else:
        cfg = VisionPipeConfig()

    asyncio.run(_run_mcp_server(cfg))


async def _run_mcp_server(cfg):
    """Run the MCP server on stdio."""
    import json
    import sys

    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import TextContent, Tool

    from vision_pipe.core.actions import DesktopActions
    from vision_pipe.core.capture import ScreenCapture
    from vision_pipe.instructions import MCP_INSTRUCTIONS
    from vision_pipe.server.mcp import VisionPipeContext, create_all_tools

    capture = ScreenCapture()
    actions = DesktopActions(failsafe=True)
    ctx = VisionPipeContext(capture=capture, actions=actions)
    tools = create_all_tools(ctx)

    server = Server("vision-pipe")

    TOOL_SCHEMAS = {
        "vision_list_windows": {"type": "object", "properties": {}},
        "vision_get_state": {"type": "object", "properties": {}},
        "vision_read_window": {"type": "object", "properties": {
            "app": {"type": "string", "description": "App name (partial match)"},
            "index": {"type": "integer", "description": "Window index if multiple (default 0)"},
        }},
        "vision_screenshot": {"type": "object", "properties": {
            "app": {"type": "string", "description": "App name, or omit for full screen"},
        }},
        "vision_get_changes": {"type": "object", "properties": {}},
        "action_click": {"type": "object", "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}, "button": {"type": "string", "enum": ["left", "right", "middle"]}, "clicks": {"type": "integer"}}, "required": ["x", "y"]},
        "action_double_click": {"type": "object", "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}}, "required": ["x", "y"]},
        "action_right_click": {"type": "object", "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}}, "required": ["x", "y"]},
        "action_type_text": {"type": "object", "properties": {"text": {"type": "string"}, "interval": {"type": "number"}}, "required": ["text"]},
        "action_press": {"type": "object", "properties": {"key": {"type": "string"}, "presses": {"type": "integer"}}, "required": ["key"]},
        "action_hotkey": {"type": "object", "properties": {"keys": {"type": "array", "items": {"type": "string"}}}, "required": ["keys"]},
        "action_scroll": {"type": "object", "properties": {"amount": {"type": "integer"}, "x": {"type": "integer"}, "y": {"type": "integer"}}, "required": ["amount"]},
        "action_drag": {"type": "object", "properties": {"start_x": {"type": "integer"}, "start_y": {"type": "integer"}, "end_x": {"type": "integer"}, "end_y": {"type": "integer"}, "duration": {"type": "number"}}, "required": ["start_x", "start_y", "end_x", "end_y"]},
        "action_move_mouse": {"type": "object", "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}}, "required": ["x", "y"]},
        "action_activate_window": {"type": "object", "properties": {"app": {"type": "string"}}, "required": ["app"]},
        "action_clipboard_copy": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
        "action_clipboard_paste": {"type": "object", "properties": {}},
        "system_check_permissions": {"type": "object", "properties": {}},
        "system_get_mouse_position": {"type": "object", "properties": {}},
        "system_get_screen_size": {"type": "object", "properties": {}},
    }

    TOOL_DESCRIPTIONS = {
        "vision_list_windows": "List all visible windows on screen (app, title, size, window_id)",
        "vision_get_state": "Get current screen state: all windows + OCR text of active window",
        "vision_read_window": "Read text in a window via OCR — returns text with bounding box coordinates for clicking",
        "vision_screenshot": "Capture screenshot of a window or full screen as base64 PNG",
        "vision_get_changes": "Get recent screen changes",
        "action_click": "Click at screen coordinates",
        "action_double_click": "Double click at screen coordinates",
        "action_right_click": "Right click at screen coordinates",
        "action_type_text": "Type text at current cursor position",
        "action_press": "Press a keyboard key (enter, tab, escape, space, up, down, etc.)",
        "action_hotkey": 'Keyboard shortcut — e.g. ["cmd","c"] for copy, ["cmd","tab"] for app switch',
        "action_scroll": "Scroll: positive=up, negative=down",
        "action_drag": "Drag from (start_x, start_y) to (end_x, end_y)",
        "action_move_mouse": "Move mouse cursor to coordinates without clicking",
        "action_activate_window": "Bring an application window to the front",
        "action_clipboard_copy": "Copy text to clipboard",
        "action_clipboard_paste": "Get text from clipboard",
        "system_check_permissions": "Check if accessibility permissions are granted for mouse/keyboard control",
        "system_get_mouse_position": "Get current mouse cursor coordinates",
        "system_get_screen_size": "Get screen dimensions in pixels",
    }

    @server.list_tools()
    async def list_tools():
        return [Tool(name=name, description=TOOL_DESCRIPTIONS[name], inputSchema=TOOL_SCHEMAS[name]) for name in tools.keys()]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        handler = tools.get(name)
        if handler is None:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
        try:
            result = await handler(**arguments)
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, default=str))]
        except Exception as e:
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    print(f"vision-pipe v2: {len(tools)} tools ready (vision + action + system)", file=sys.stderr)
    async with stdio_server() as (read, write):
        init_options = server.create_initialization_options()
        init_options.instructions = MCP_INSTRUCTIONS
        await server.run(read, write, init_options)


@main.command()
def snapshot():
    """Take a single screenshot and analyze it."""
    click.echo("Capturing screen...")
    click.echo("Snapshot mode — connect a provider to analyze.")


@main.command()
def providers():
    """List available vision providers."""
    builtins = {
        "ollama": "Ollama (local models)",
        "sampling": "MCP Sampling (via agent)",
        "gemini": "Google Gemini (API key)",
        "anthropic": "Anthropic Claude (API key)",
        "openai": "OpenAI GPT-4o (API key)",
        "apple-vision": "Apple Vision Framework (native)",
        "mlx": "MLX (Apple Silicon)",
    }
    for name, desc in builtins.items():
        click.echo(f"  {name:20s} {desc}")


@main.command()
@click.option("--provider", help="Provider to benchmark")
@click.option("--compare", help="Compare providers ('all' or comma-separated)")
@click.option("--phase", type=click.Choice(["peripheral", "foveal"]), help="Benchmark only one phase")
def benchmark(provider: str | None, compare: str | None, phase: str | None):
    """Run benchmarks on vision providers."""
    click.echo("Benchmark suite — place screenshots in benchmarks/screenshots/ and run again.")


if __name__ == "__main__":
    main()
