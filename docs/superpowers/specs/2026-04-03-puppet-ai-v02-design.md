# puppet-ai v0.2 — CDP Browser + AI Vision + Best Practices

## Goal

Major upgrade inspired by best practices from top MCP servers (Playwright MCP 30k stars, Chrome DevTools MCP 33k stars, Peekaboo 3k stars, browser-use 85k stars):

1. Chrome DevTools Protocol (CDP) for reliable browser automation (DOM access, form filling, JS execution)
2. AI vision agent that automatically analyzes screenshots via a fast model
3. Element ID overlay on screenshots (from Peekaboo) — agent says "click element 7" instead of coordinates
4. Accessibility tree snapshot (from Playwright MCP) — 100x cheaper than screenshots for web content
5. Tab management — list/switch tabs via CDP
6. Natural language browser actions — `browser_act("fill the login form")` via AI

## Architecture

```
AI Agent (Claude Code, Codex, Gemini, ...)
    ↕ MCP (stdio)
puppet-ai server
    ├── Vision:   OCR + screenshot + AI analysis (auto)
    ├── Browser:  Chrome DevTools Protocol (DOM)
    ├── Actions:  pyautogui (desktop)
    └── System:   permissions, mouse, screen
```

Three control layers with distinct prefixes:
- `vision_*` — perception (OCR, screenshots, AI analysis)
- `browser_*` — browser via CDP (DOM, forms, JS)
- `action_*` — desktop via pyautogui (mouse, keyboard)

## Component 1: CDP Browser Engine

### Connection Strategy

1. On first `browser_*` call, try connecting to Chrome debug port (default 9222)
2. If Chrome is running without debug port — return error with instructions to restart Chrome with `--remote-debugging-port=9222`
3. If Chrome is not running — attempt to launch it with the debug flag automatically

Connection is lazy (first use) and cached for the session.

### New MCP Tools

| Tool | Input | Description |
|------|-------|-------------|
| `browser_fill(selector, value)` | CSS selector + text value | Fill an input/textarea by CSS selector. Clears existing value first. |
| `browser_click(selector)` | CSS selector | Click an element by CSS selector. Waits for element to exist. |
| `browser_evaluate(js)` | JavaScript string | Execute JS in page context, return result as string. |
| `browser_get_text()` | — | Get full page text via `document.body.innerText` (DOM, not OCR). |
| `browser_navigate(url)` | URL string | Navigate current tab to URL. Waits for load. |
| `browser_snapshot()` | — | Get accessibility tree of current page (structured, 100x cheaper than screenshot). |
| `browser_list_tabs()` | — | List all open Chrome tabs (title, url, id). |
| `browser_switch_tab(tab_id)` | Tab ID | Switch to a specific tab. |
| `browser_act(action)` | Natural language string | AI-powered action: "fill the login form", "click Submit". Uses vision agent to understand page and execute. |

### Implementation

File: `src/puppet_ai/core/cdp.py`

- Pure websocket connection to `ws://localhost:9222`
- Uses Chrome DevTools Protocol JSON-RPC
- Dependencies: `websockets` package (add to pyproject.toml)
- Methods: `connect()`, `send_command(method, params)`, `evaluate(js)`, `close()`
- All commands go through `Runtime.evaluate` or `DOM.*` methods
- Connection auto-reconnects on tab change

### Tool Schemas (cli.py additions)

```python
"browser_fill": {
    "type": "object",
    "properties": {
        "selector": {"type": "string", "description": "CSS selector for the input field"},
        "value": {"type": "string", "description": "Text to fill in"},
    },
    "required": ["selector", "value"],
}
"browser_click": {
    "type": "object",
    "properties": {
        "selector": {"type": "string", "description": "CSS selector to click"},
    },
    "required": ["selector"],
}
"browser_evaluate": {
    "type": "object",
    "properties": {
        "js": {"type": "string", "description": "JavaScript to execute"},
    },
    "required": ["js"],
}
"browser_get_text": {"type": "object", "properties": {}}
"browser_navigate": {
    "type": "object",
    "properties": {
        "url": {"type": "string", "description": "URL to navigate to"},
    },
    "required": ["url"],
}
```

### Security

- `browser_evaluate` runs arbitrary JS — same trust model as the agent itself
- URL validation: only `http://` and `https://` for `browser_navigate`
- No file:// or javascript: URLs

## Component 2: AI Vision Agent

### Behavior

`vision_screenshot(app)` now returns:
```json
{
    "image_base64": "...",
    "width": 800,
    "height": 450,
    "ai_description": "Safari showing Google search results for 'puppet-ai'. The page has 10 results, first one is the GitHub repo..."
}
```

AI analysis happens automatically on every screenshot call. If no AI provider is available, `ai_description` is omitted and behavior is identical to v0.1.

### Provider Resolution (priority order)

1. **Environment variables**: `PUPPET_VISION_PROVIDER` + `PUPPET_VISION_MODEL` + standard API key env vars
2. **Config file**: `puppet-ai.yaml` → `vision_agent` section
3. **MCP sampling**: request to host agent (Claude Code uses haiku, others use their own model)
4. **Fallback**: no AI analysis, screenshot-only (graceful degradation)

### Supported Providers

| Provider | Env var for key | Default model |
|----------|----------------|---------------|
| `anthropic` | `ANTHROPIC_API_KEY` | `claude-haiku-4-5-20251001` |
| `openai` | `OPENAI_API_KEY` | `gpt-4o-mini` |
| `gemini` | `GEMINI_API_KEY` | `gemini-2.0-flash` |
| `ollama` | — (local) | `llava` |

### Config Format

```yaml
vision_agent:
  provider: anthropic
  model: claude-haiku-4-5-20251001
  api_key_env: ANTHROPIC_API_KEY
  prompt: "Describe what you see on this screen. Be concise."
```

Environment variable overrides:
```
PUPPET_VISION_PROVIDER=anthropic
PUPPET_VISION_MODEL=claude-haiku-4-5-20251001
```

### MCP Sampling Fallback

When no provider is configured, puppet-ai sends a `sampling/createMessage` request to the host agent with the screenshot image. The host agent (e.g. Claude Code) processes it through its own model selection. In Claude Code this routes to haiku automatically.

### Implementation

File: `src/puppet_ai/core/vision_agent.py`

- `VisionAgent` class with `async analyze(image_bytes, prompt) -> str`
- Provider resolution on first call, cached
- Timeout: 10s max per analysis
- On failure: return empty string (never block screenshot)

### System Prompt for Analysis

Default prompt sent with each screenshot:
```
Describe what you see on this screen in 2-3 sentences. Focus on: what app is open, what content is visible, and any interactive elements (buttons, links, forms). Be concise.
```

## Changes to Existing Code

### pyproject.toml
- Add `websockets>=12.0` to dependencies
- Bump version to `0.2.0`

### src/puppet_ai/server/mcp.py
- Add 5 new `browser_*` tool handlers in `create_all_tools()`
- Modify `vision_screenshot()` to call `VisionAgent.analyze()` after capture
- Add `CDPClient` to `VisionPipeContext`
- Add `VisionAgent` to `VisionPipeContext`

### src/puppet_ai/cli.py
- Add 5 new tool schemas and descriptions
- Update version print

### src/puppet_ai/instructions.py
- Add `browser_*` tools section to MCP_INSTRUCTIONS
- Update strategy: "For web forms and DOM interaction, use browser_* tools"

### New Files
- `src/puppet_ai/core/cdp.py` — CDP websocket client
- `src/puppet_ai/core/vision_agent.py` — AI screenshot analyzer

## What Does NOT Change

- All 27 existing tools (vision_*, action_*, system_*)
- OCR engine, PII filter, OCR cache, Accessibility API
- Desktop actions via pyautogui
- CLI command name and config format

## Testing

- CDP: test against live Chrome on example.com (fill form, click link, read text, evaluate JS)
- Vision Agent: test with mock provider, verify graceful fallback
- Integration: full cycle — browser_navigate → vision_screenshot (with AI) → browser_fill → verify
