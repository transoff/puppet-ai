# puppet-ai + Cursor IDE

Give Cursor full macOS desktop control: OCR reading, mouse/keyboard input, and UI element automation.

## Prerequisites

```bash
pip install puppet-ai
# Grant accessibility permissions: System Settings → Privacy & Security → Accessibility
```

## Configuration

### Option 1: Config File

Edit `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "puppet-ai": {
      "command": "puppet-ai",
      "args": ["serve"]
    }
  }
}
```

### Option 2: Settings UI

In Cursor: Settings → Tools & MCP → Add Server
- Name: `puppet-ai`
- Command: `puppet-ai serve`

Restart Cursor after changes.

## Verify It Works

Ask Cursor: `"Read what's currently on my screen"`

The agent will capture and describe your desktop content.

## Available Tools

- `list_windows` — Get all open windows
- `get_state` — Screen state + OCR of active window
- `read_window(app="AppName")` — Read specific application
- `describe(region)` — Detailed region analysis
- `left_click`, `right_click`, `type`, `key` — Input controls
- `scroll`, `screenshot` — Navigation and capture

See [main README](../README.md) for full API reference.
