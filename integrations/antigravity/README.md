# puppet-ai + Google Antigravity

Enable Antigravity agents to control your macOS desktop with full screen reading and automation capabilities.

## Prerequisites

```bash
pip install puppet-ai
# Grant accessibility permissions: System Settings → Privacy & Security → Accessibility
```

## Configuration

### Option 1: Config File

Edit `.antigravity/settings.json` or `~/.config/antigravity/settings.json`:

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

### Option 2: MCP Marketplace

Use Antigravity's MCP Marketplace UI to add puppet-ai (if published).

Restart Antigravity after configuration.

## Verify It Works

Ask your Antigravity agent: `"Show me what's on the desktop right now"`

The agent will use puppet-ai tools to read and describe your screen.

## Available Tools

- `list_windows` — All open applications
- `get_state` — Current screen + OCR of active window
- `read_window(app="AppName")` — Read app contents
- `describe(region)` — Detailed region analysis
- `left_click`, `right_click`, `type`, `key` — Input automation
- `scroll`, `screenshot` — Navigation and capture

See [main README](../README.md) for full API reference.
