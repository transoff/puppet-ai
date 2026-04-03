"""Benchmark runner for puppet-ai providers.

Usage:
    python run_benchmark.py --provider ollama/moondream2
    python run_benchmark.py --compare all
    python run_benchmark.py --phase peripheral --provider gemini-flash
"""
from __future__ import annotations
import asyncio, json, time
from pathlib import Path
import click

SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"
EXPECTED_DIR = Path(__file__).parent / "expected"


def load_expected(name: str) -> dict | None:
    path = EXPECTED_DIR / f"{name}.json"
    if path.exists():
        return json.loads(path.read_text())
    return None


def calculate_accuracy(result: dict, expected: dict) -> float:
    if not expected:
        return 0.0
    matches = 0
    total = 0
    for key, value in expected.items():
        total += 1
        if key in result:
            if str(result[key]).lower() == str(value).lower():
                matches += 1
            elif str(value).lower() in str(result[key]).lower():
                matches += 0.5
    return (matches / total) * 100 if total > 0 else 0.0


async def benchmark_provider(provider, screenshots: list[Path], phase: str | None):
    results = []
    for screenshot in screenshots:
        name = screenshot.stem
        image_bytes = screenshot.read_bytes()
        expected = load_expected(name)
        if phase != "foveal":
            start = time.perf_counter()
            scan_result = await provider.scan(image_bytes)
            scan_latency = time.perf_counter() - start
            scan_accuracy = 0.0
            if expected and "summary" in expected:
                scan_accuracy = calculate_accuracy({"summary": scan_result.summary}, {"summary": expected["summary"]})
            results.append({"name": name, "phase": "peripheral", "latency": round(scan_latency, 3), "accuracy": round(scan_accuracy, 1), "regions_found": len(scan_result.regions)})
    return results


@click.command()
@click.option("--provider", help="Provider to benchmark")
@click.option("--compare", help="Compare providers: 'all' or comma-separated")
@click.option("--phase", type=click.Choice(["peripheral", "foveal"]))
def main(provider: str | None, compare: str | None, phase: str | None):
    screenshots = sorted(SCREENSHOTS_DIR.glob("*.png"))
    if not screenshots:
        click.echo("No screenshots found in benchmarks/screenshots/")
        click.echo("Add PNG screenshots to benchmark against.")
        return
    click.echo(f"Found {len(screenshots)} screenshots")
    click.echo("Benchmark runner ready. Provider integration pending.")


if __name__ == "__main__":
    main()
