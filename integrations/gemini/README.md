# puppet-ai + Google Gemini

Give Gemini CLI full control of your macOS desktop: OCR screen reading, mouse, keyboard, and UI automation.

## Prerequisites

```bash
pip install puppet-ai
# Grant accessibility permissions: System Settings → Privacy & Security → Accessibility
```

## Configuration

Edit `~/.gemini/settings.json`:

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

Restart Gemini after changes.

## Verify It Works

In Gemini CLI, ask: `"Read what's on my screen"`

The agent will capture your desktop and describe visible content.

Check connection with `/mcp` command in Gemini CLI.

## Available Tools

- `list_windows` — Get all open windows
- `get_state` — Screen state + OCR text
- `read_window(app="AppName")` — Read specific window
- `describe(region)` — Detailed region analysis
- `left_click`, `right_click`, `type`, `key` — Input controls
- `scroll`, `screenshot` — Navigation

See [main README](../README.md) for full API reference.
