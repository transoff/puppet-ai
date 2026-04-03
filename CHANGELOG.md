# Changelog

## 0.1.0 (2026-04-03)

Initial release.

### Features

- **27 MCP tools** for full computer control — vision, actions, system
- **Native macOS OCR** via Apple Vision Framework (Russian + English)
- **Per-window capture** via CGWindowList — no app switching needed
- **Accessibility API** — detect buttons, links, checkboxes, text fields
- **Computer control** — click, type, scroll, drag, hotkeys, clipboard
- **Smart tools** — `action_click_text`, `action_click_and_wait`, `action_open_url`
- **PII protection** — auto-mask API keys, passwords, credit cards in OCR output
- **OCR cache** — 7x speedup on repeated reads, auto-invalidation after actions
- **Retina display** support — automatic coordinate scaling
- **Agent-agnostic** — works with Claude Code, OpenClaw, any MCP client
- **System prompt** — built-in instructions teach agents how to use the tools
