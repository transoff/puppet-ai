# puppet-ai + Windsurf (Codeium)

Enable Windsurf's Cascade agent to control your macOS desktop with screen reading and automation.

## Prerequisites

```bash
pip install puppet-ai
# Grant accessibility permissions: System Settings → Privacy & Security → Accessibility
```

## Configuration

### Option 1: Config File

Edit `~/.codeium/windsurf/mcp_config.json`:

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

In Windsurf, open Cascade panel → MCP Marketplace → Search and add puppet-ai.

Restart Windsurf after configuration.

## Verify It Works

Ask Cascade: `"What windows do I have open right now?"`

The agent will use puppet-ai to list and describe your desktop.

## Available Tools

- `list_windows` — All open applications
- `get_state` — Current screen + OCR of active window
- `read_window(app="AppName")` — Read application contents
- `describe(region)` — Detailed region analysis
- `left_click`, `right_click`, `type`, `key` — Input automation
- `scroll`, `screenshot` — Navigation and capture

See [main README](../README.md) for full API reference.
