# puppet-ai + Zed Editor

Enable Zed's assistant to control your macOS desktop with OCR screen reading and full automation.

## Prerequisites

```bash
pip install puppet-agent
# Grant accessibility permissions: System Settings → Privacy & Security → Accessibility
```

## Configuration

Edit `~/.config/zed/settings.json`:

```json
{
  "context_servers": {
    "puppet-ai": {
      "command": {
        "path": "puppet-ai",
        "args": ["serve"]
      }
    }
  }
}
```

Restart Zed after changes.

## Verify It Works

Ask Zed's assistant: `"Show me what windows are open on my screen"`

The agent will use puppet-ai tools to read and list your desktop.

## Available Tools

- `list_windows` — All open windows
- `get_state` — Current screen + OCR of active window
- `read_window(app="AppName")` — Read application contents
- `describe(region)` — Detailed region analysis
- `left_click`, `right_click`, `type`, `key` — Input controls
- `scroll`, `screenshot` — Navigation and capture

See [main README](../README.md) for full API reference.
