# puppet-ai + Claude Code

Give Claude Code full macOS control: screen reading, mouse/keyboard input, and UI element detection.

## Prerequisites

```bash
pip install puppet-agent
# Grant accessibility permissions: System Settings → Privacy & Security → Accessibility
```

## Configuration

Edit `~/.claude/settings.json`:

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

Restart Claude Code after changes.

## Verify It Works

Ask Claude Code: `"Read my screen and tell me what windows are open"`

The agent will use puppet-ai tools to capture your screen and describe what's visible.

## Available Tools

- `list_windows` — Get all open windows with titles
- `get_state` — Current screen state + OCR text of active window
- `read_window(app="AppName")` — Read text from specific app
- `describe(region)` — Detailed description of screen area
- `left_click`, `right_click`, `type`, `key` — Input controls
- `scroll`, `screenshot` — Navigation and capture

See [main README](../README.md) for full API reference.
