# puppet-ai + OpenAI Codex

Enable Codex to control your macOS desktop with screen reading and input automation.

## Prerequisites

```bash
pip install puppet-agent
# Grant accessibility permissions: System Settings → Privacy & Security → Accessibility
```

## Configuration

### Option 1: Config File

Edit `~/.codex/config.toml`:

```toml
[mcp_servers.puppet-ai]
command = "puppet-ai"
args = ["serve"]
```

### Option 2: CLI

```bash
codex mcp add puppet-ai -- puppet-ai serve
```

Restart Codex after changes.

## Verify It Works

Ask Codex: `"What's currently on my screen?"`

The agent will use puppet-ai tools to capture and describe your desktop.

## Available Tools

- `list_windows` — All open windows
- `get_state` — Screen state + OCR of active window
- `read_window(app="AppName")` — Read specific application
- `describe(region)` — Detailed area description
- `left_click`, `right_click`, `type`, `key` — Input controls
- `scroll`, `screenshot` — Navigation

See [main README](../README.md) for full API reference.
