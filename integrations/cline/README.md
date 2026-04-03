# puppet-ai + Cline

Give Cline (VS Code extension) full macOS desktop control with OCR screen reading and input automation.

## Prerequisites

```bash
pip install puppet-ai
# Grant accessibility permissions: System Settings → Privacy & Security → Accessibility
```

## Configuration

In VS Code, open Cline Settings → MCP Servers → Add:

```json
{
  "puppet-ai": {
    "command": "puppet-ai",
    "args": ["serve"]
  }
}
```

Restart VS Code after adding the server.

## Verify It Works

Ask Cline: `"Take a screenshot and tell me what you see"`

The agent will capture your screen and describe what's visible.

## Available Tools

- `list_windows` — Get all open windows
- `get_state` — Screen state + OCR of active window
- `read_window(app="AppName")` — Read specific application
- `describe(region)` — Detailed region analysis
- `left_click`, `right_click`, `type`, `key` — Input controls
- `scroll`, `screenshot` — Navigation and capture

See [main README](../README.md) for full API reference.
