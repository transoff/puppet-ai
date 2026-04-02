# OpenClaw Integration

Give your OpenClaw agent eyes with vision-pipe.

## Setup (30 seconds)

### 1. Register MCP server

```bash
openclaw mcp set vision-pipe '{"command":"vision-pipe","args":["serve","--preset","fast"]}'
```

### 2. Add vision to SOUL.md

Append the contents of `SOUL_VISION.md` to your agent's SOUL.md:

```bash
cat integrations/openclaw/SOUL_VISION.md >> ~/.openclaw/workspace/SOUL.md
```

### 3. Restart gateway

```bash
openclaw gateway --force
```

### 4. Test

Send your bot a message: "What's on my screen?"

The agent will automatically call `list_windows` and `get_state` to describe what it sees.
