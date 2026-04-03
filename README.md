# puppet-ai

Full computer control for AI agents — see, click, type, scroll via MCP.

Give any AI agent eyes and hands. puppet-ai captures the screen, reads text via native OCR, detects UI elements, and controls mouse + keyboard. Works with any app on macOS — browsers, desktop apps, games, terminals.

## Why puppet-ai?

- **Fast** — native macOS OCR in ~0.5s, 7x faster with caching
- **Universal** — works with ANY app, not just browsers
- **Agent-agnostic** — MCP standard, plug into any AI agent
- **Secure** — auto-masks API keys, passwords, credit cards, emails in OCR output
- **Complete** — 27 tools: vision + actions + system
- **Private** — all processing on-device, no data leaves your Mac

## Quick Start

### 1. Install

```bash
pip install puppet-ai
```

### 2. Enable Accessibility

System Settings → Privacy & Security → Accessibility → enable your terminal/IDE app.

### 3. Connect to your AI agent

puppet-ai is an MCP server. Connect it to any MCP-compatible agent below, then ask the agent to interact with your computer.

---

## Integrations

### Claude Code

Add to `~/.claude/settings.json`:

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

### OpenAI Codex CLI

Add to `~/.codex/config.toml`:

```toml
[mcp_servers.puppet-ai]
command = "puppet-ai"
args = ["serve"]
```

Or via CLI:

```bash
codex mcp add puppet-ai -- puppet-ai serve
```

### Google Gemini CLI

Add to `~/.gemini/settings.json`:

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

Verify: launch `gemini` and run `/mcp` to check connection.

### Google Antigravity

Via MCP settings in Antigravity, or add to your project's `.antigravity/settings.json`:

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

### Cursor

Add to `~/.cursor/mcp.json`:

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

Or: Cursor Settings → Tools & MCP → Add Server.

### Windsurf

Add to `~/.codeium/windsurf/mcp_config.json`:

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

### Cline (VS Code)

In VS Code, open Cline settings → MCP Servers → Add:

```json
{
  "puppet-ai": {
    "command": "puppet-ai",
    "args": ["serve"]
  }
}
```

### Zed

Add to Zed settings (`~/.config/zed/settings.json`):

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

### OpenClaw

Add to your agent's MCP config:

```yaml
mcp_servers:
  puppet-ai:
    command: puppet-ai
    args: [serve]
```

### Any MCP Client

puppet-ai speaks MCP over stdio. Spawn it as a subprocess:

```python
import subprocess
proc = subprocess.Popen(
    ["puppet-ai", "serve"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
)
# Communicate via MCP JSON-RPC over stdin/stdout
```

Works with any agent that supports the [Model Context Protocol](https://modelcontextprotocol.io).

Detailed setup guides: [`integrations/`](integrations/)

---

## Tools

### Vision (see the screen)

| Tool | Description |
|------|-------------|
| `vision_list_windows` | List all open windows (app, title, size) |
| `vision_read_window(app)` | Read text via OCR with bounding boxes for clicking |
| `vision_screenshot(app)` | Capture screenshot as base64 JPEG |
| `vision_get_state` | Full screen state: all windows + active window text |
| `vision_ui_elements(app)` | Get UI elements via Accessibility API (buttons, links, checkboxes) |

### Actions (control the computer)

| Tool | Description |
|------|-------------|
| `action_click(x, y)` | Click at coordinates |
| `action_click_text(text, app)` | Find text on screen and click it — no coordinates needed |
| `action_click_and_wait(text, app)` | Click text, wait for screen to stabilize, return new state |
| `action_type_safe(text)` | Type text via clipboard paste (works with any keyboard layout) |
| `action_open_url(url)` | Open URL in browser (http/https only) |
| `action_scroll(amount, app)` | Scroll up/down in an app |
| `action_hotkey(keys)` | Keyboard shortcut (e.g. `["cmd", "c"]`) |
| `action_press(key)` | Press a key (enter, tab, escape, etc.) |
| `action_drag(...)` | Drag and drop |
| `action_activate_window(app)` | Bring app to front |
| `action_clipboard_copy(text)` | Copy to clipboard |
| `action_clipboard_paste()` | Paste from clipboard |

### System

| Tool | Description |
|------|-------------|
| `system_check_permissions` | Check accessibility access |
| `system_get_screen_size` | Screen dimensions |
| `system_get_mouse_position` | Current cursor position |
| `system_unmask(reason)` | Temporarily disable PII masking |
| `system_mask()` | Re-enable PII masking |

## How It Works

```
AI Agent (Claude, Codex, Gemini, Cursor, Windsurf, ...)
    ↕ MCP protocol (stdio)
puppet-ai server
    ├── Vision: Apple Vision OCR + CGWindowList capture
    ├── Accessibility: AXUIElement tree (buttons, links, fields)
    ├── Actions: pyautogui (mouse, keyboard, scroll)
    └── Security: PII regex filter (API keys, cards, passwords, emails)
```

**The loop:**
1. **Look** — `vision_read_window("Safari")` → text + coordinates
2. **Decide** — agent plans next action
3. **Act** — `action_click_text("Sign In")` → clicks center of text
4. **Verify** — `vision_read_window` again → confirm it worked
5. **Repeat**

## Features

### Native macOS OCR

Uses Apple Vision Framework — no external API, no GPU needed, works offline. Supports Russian and English.

### Per-Window Capture

Captures specific windows via CGWindowList without switching apps or stealing focus.

### Smart Coordinates

OCR returns absolute screen coordinates with Retina scaling handled automatically.

### OCR Cache

Repeated reads of unchanged windows are 7x faster. Cache auto-invalidates after any action.

### PII Protection

Sensitive data is automatically masked in OCR output:
- API keys: `sk-1***ef`
- Credit cards: `4111***1111`
- Emails: `user***com`
- Passwords in forms
- Crypto keys

### Accessibility API

Detect interactive UI elements — buttons, checkboxes, links, text fields — with exact clickable coordinates.

### Built-in Agent Instructions

The MCP server includes a system prompt that teaches agents how to use all 27 tools, macOS keyboard shortcuts, and the look-decide-act-verify loop.

## Security

- **All data stays on your Mac** — no telemetry, no analytics, no external calls
- **PII auto-masking** — API keys, credit cards, emails, passwords masked before reaching the agent
- **URL validation** — only `http://` and `https://` allowed, `file://` blocked
- **Input sanitization** — app names validated to prevent injection
- **Browser allowlist** — only known browsers accepted (Chrome, Safari, Firefox, Arc, etc.)
- **Failsafe** — pyautogui failsafe enabled by default (move mouse to corner to abort)

## Examples

```python
import asyncio
from puppet_ai.core.capture import ScreenCapture
from puppet_ai.core.actions import DesktopActions
from puppet_ai.server.mcp import VisionPipeContext, create_all_tools

async def main():
    ctx = VisionPipeContext(
        capture=ScreenCapture(),
        actions=DesktopActions(failsafe=True),
    )
    tools = create_all_tools(ctx)

    # See what's on screen
    windows = await tools["vision_list_windows"]()
    for w in windows:
        print(f"{w['app']:20s} — {w['title'][:50]}")

    # Read a window
    page = await tools["vision_read_window"](app="Safari")
    print(page["text"][:500])

    # Click text on screen
    await tools["action_click_text"](text="Sign In", app="Safari")

    # Open a URL
    await tools["action_open_url"](url="https://example.com", browser="Safari")

asyncio.run(main())
```

More examples in [`examples/`](examples/).

## Configuration

```yaml
# puppet-ai.yaml
ocr:
  languages: ["en", "ru"]
  mode: accurate  # or "fast"

pii:
  enabled: true
  categories: [api_keys, credit_cards, crypto_keys, emails, passwords]

capture:
  max_width: 800
  format: jpeg
  quality: 75
```

Presets:

```bash
puppet-ai serve --preset fast      # speed over accuracy
puppet-ai serve --preset balanced  # default
puppet-ai serve --preset quality   # max accuracy
```

## Requirements

- macOS 13+ (Ventura or later)
- Python 3.11+
- Accessibility permissions enabled

## Author

**Daniel Starkov**

- Twitter: [@retardTransoff](https://x.com/retardTransoff)
- LinkedIn: [Daniel Starkov](https://www.linkedin.com/in/daniel-starkov-568baa39b/)

## License

MIT
