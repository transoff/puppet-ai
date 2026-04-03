# tests/test_cli.py
from click.testing import CliRunner
from puppet_ai.cli import main


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "serve" in result.output


def test_cli_serve_help():
    runner = CliRunner()
    result = runner.invoke(main, ["serve", "--help"])
    assert result.exit_code == 0
    assert "--preset" in result.output
    assert "--config" in result.output


def test_cli_snapshot_help():
    runner = CliRunner()
    result = runner.invoke(main, ["snapshot", "--help"])
    assert result.exit_code == 0


def test_cli_providers_help():
    runner = CliRunner()
    result = runner.invoke(main, ["providers", "--help"])
    assert result.exit_code == 0


def test_cli_benchmark_help():
    runner = CliRunner()
    result = runner.invoke(main, ["benchmark", "--help"])
    assert result.exit_code == 0
    assert "--provider" in result.output
