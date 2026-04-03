# puppet-ai + OpenClaw

Give OpenClaw agents full macOS desktop control with OCR screen reading and automation.

## Prerequisites

```bash
pip install puppet-agent
# Grant accessibility permissions: System Settings → Privacy & Security → Accessibility
```

## Configuration

### Step 1: Register MCP Server

```bash
openclaw mcp set puppet-ai '{"command":"puppet-ai","args":["serve"]}'
```

### Step 2: Add Vision Instructions

Append vision capabilities to your agent's SOUL.md:

```bash
cat integrations/openclaw/SOUL_VISION.md >> ~/.openclaw/workspace/SOUL.md
```

### Step 3: Restart Gateway

```bash
openclaw gateway --force
```

## Verify It Works

Message your agent: `"What's currently on my screen?"`

The agent will use puppet-ai tools to read and describe your desktop.

## Available Tools

- `list_windows` — All open windows with titles
- `get_state` — Current screen + OCR of active window
- `read_window(app="AppName")` — Read specific application
- `describe(region)` — Detailed region analysis
- `left_click`, `right_click`, `type`, `key` — Input controls
- `scroll`, `screenshot` — Navigation and capture

See [main README](../README.md) for full API reference.
