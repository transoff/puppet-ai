# src/vision_pipe/cli.py
from __future__ import annotations
import asyncio
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
    from vision_pipe.config.schema import VisionPipeConfig
    from vision_pipe.config.presets import get_preset

    if preset:
        cfg = get_preset(preset)
    elif config:
        cfg = VisionPipeConfig.from_yaml(Path(config))
    else:
        cfg = VisionPipeConfig()

    click.echo(f"Starting vision-pipe MCP server...")
    click.echo(f"  Peripheral: {cfg.peripheral.provider}")
    click.echo(f"  Foveal: {cfg.foveal.provider}")
    click.echo(f"  Capture FPS: {cfg.capture.fps}")
    # MCP server startup will be wired in integration


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
