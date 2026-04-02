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
    import json
    import sys

    from vision_pipe.config.presets import get_preset
    from vision_pipe.config.schema import VisionPipeConfig

    if preset:
        cfg = get_preset(preset)
    elif config:
        cfg = VisionPipeConfig.from_yaml(Path(config))
    else:
        cfg = VisionPipeConfig()

    # All output to stderr — stdout is reserved for MCP protocol
    print(f"vision-pipe: peripheral={cfg.peripheral.provider}, foveal={cfg.foveal.provider}", file=sys.stderr)

    asyncio.run(_run_mcp_server(cfg))


async def _run_mcp_server(cfg):
    """Run the MCP server on stdio."""
    import json
    import sys

    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import TextContent, Tool

    from vision_pipe.core.capture import ScreenCapture
    from vision_pipe.core.foveal import FovealFocus
    from vision_pipe.core.peripheral import PeripheralVision
    from vision_pipe.core.world_model import WorldModel
    from vision_pipe.providers.ollama import OllamaProvider
    from vision_pipe.server.mcp import VisionMCPContext, create_vision_tools

    # Build components
    peripheral_model = cfg.peripheral.provider.split("/")[-1] if "/" in cfg.peripheral.provider else cfg.peripheral.provider
    peripheral_provider = OllamaProvider(model=peripheral_model)
    foveal_provider = OllamaProvider(model=peripheral_model)  # same for now

    peripheral = PeripheralVision(
        provider=peripheral_provider,
        resolution=cfg.peripheral.resolution_tuple(),
    )
    foveal = FovealFocus(provider=foveal_provider)
    capture = ScreenCapture()
    world_model = WorldModel()

    ctx = VisionMCPContext(
        world_model=world_model,
        peripheral=peripheral,
        foveal=foveal,
        capture=capture,
    )
    tools = create_vision_tools(ctx)

    server = Server("vision-pipe")

    @server.list_tools()
    async def list_tools():
        return [
            Tool(
                name="get_state",
                description="Get current screen state: all open windows + OCR text of the active (frontmost) window. This is your primary 'look at the screen' tool.",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="read_window",
                description="Read text content of a specific window via native OCR. Use this to read what's inside Chrome, Safari, Terminal, or any app. Returns all visible text.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "app": {
                            "type": "string",
                            "description": "App name to find (e.g. 'Chrome', 'Safari', 'Terminal', 'Spotify'). Case-insensitive partial match.",
                        },
                        "index": {
                            "type": "integer",
                            "description": "Which window if multiple matches (0 = frontmost). Default: 0",
                        },
                    },
                },
            ),
            Tool(
                name="describe",
                description="Describe screen via VLM vision model. Falls back to OCR if VLM unavailable.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "region": {
                            "type": "string",
                            "description": "Region name from world model, or omit for full screen scan",
                        },
                    },
                },
            ),
            Tool(
                name="get_changes",
                description="Get recent screen changes since last check",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "since": {
                            "type": "string",
                            "description": "ISO timestamp to get changes since",
                        },
                    },
                },
            ),
            Tool(
                name="focus",
                description="Set attention focus on a screen region — watch it more closely",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "region": {"type": "string"},
                        "priority": {"type": "string", "enum": ["high", "normal"]},
                    },
                    "required": ["region"],
                },
            ),
            Tool(
                name="ignore",
                description="Ignore a screen region (e.g. ads, static UI)",
                inputSchema={
                    "type": "object",
                    "properties": {"region": {"type": "string"}},
                    "required": ["region"],
                },
            ),
            Tool(
                name="list_windows",
                description="List all visible windows on screen with their titles and apps",
                inputSchema={"type": "object", "properties": {}},
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        if name == "list_windows":
            windows = capture.list_windows()
            result = [
                {"window_id": w.window_id, "app": w.owner, "title": w.title, "width": w.width, "height": w.height}
                for w in windows
            ]
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

        handler = tools.get(name)
        if handler is None:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
        result = await handler(**arguments)
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

    print("vision-pipe: MCP server starting on stdio", file=sys.stderr)
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


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
