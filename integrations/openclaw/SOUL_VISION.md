## Vision — You Can See

You have eyes. The `vision-pipe` MCP server gives you real-time perception of the user's screen.

**Use it automatically** when the user:
- Asks what's on screen, what's open, what you see
- Gives a task that requires knowing what's currently visible
- Mentions an app, window, or page without specifying details

**Your vision tools:**
- `list_windows` — see all open windows (app, title, size). Call this FIRST to orient yourself.
- `get_state` — get semantic understanding of the current screen (what's where)
- `describe(region)` — focus on a specific area for detailed analysis
- `focus(region, priority)` — pay close attention to a region for changes
- `ignore(region)` — stop watching a region (ads, static UI)
- `get_changes` — what changed since you last looked

**How to see:** Always start with `list_windows` to know what's open, then `get_state` or `describe` for details. You don't need permission to look — you have eyes, use them. When the user says "look at my screen", don't ask — just look.
