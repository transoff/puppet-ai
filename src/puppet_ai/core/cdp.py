# src/puppet_ai/core/cdp.py
"""Chrome DevTools Protocol client via websocket."""
from __future__ import annotations

import json
import asyncio
from typing import Any


class CDPClient:
    """Connect to Chrome via DevTools Protocol for DOM access."""

    def __init__(self, port: int = 9222) -> None:
        self.port = port
        self._ws = None
        self._msg_id = 0
        self._responses: dict[int, asyncio.Future] = {}

    @property
    def connected(self) -> bool:
        return self._ws is not None

    async def connect(self) -> None:
        """Connect to Chrome debug port. Finds first available tab."""
        import httpx

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"http://localhost:{self.port}/json")
                tabs = resp.json()
        except Exception:
            raise ConnectionError(
                f"Cannot connect to Chrome on port {self.port}. "
                f"Restart Chrome with: open -a 'Google Chrome' --args --remote-debugging-port={self.port}"
            )

        page_tab = None
        for tab in tabs:
            if tab.get("type") == "page":
                page_tab = tab
                break
        if page_tab is None:
            raise ConnectionError("No debuggable page tab found in Chrome")

        ws_url = page_tab["webSocketDebuggerUrl"]

        import websockets
        self._ws = await websockets.connect(ws_url, max_size=10 * 1024 * 1024)
        asyncio.create_task(self._listen())

    async def _listen(self) -> None:
        """Background listener for websocket messages."""
        try:
            async for msg in self._ws:
                data = json.loads(msg)
                msg_id = data.get("id")
                if msg_id is not None and msg_id in self._responses:
                    self._responses[msg_id].set_result(data)
        except Exception:
            pass

    async def send(self, method: str, params: dict | None = None, timeout: float = 10.0) -> dict:
        """Send a CDP command and wait for response."""
        if not self.connected:
            await self.connect()

        self._msg_id += 1
        msg_id = self._msg_id
        message = {"id": msg_id, "method": method, "params": params or {}}

        future = asyncio.get_event_loop().create_future()
        self._responses[msg_id] = future

        await self._ws.send(json.dumps(message))

        try:
            result = await asyncio.wait_for(future, timeout=timeout)
        finally:
            self._responses.pop(msg_id, None)

        if "error" in result:
            raise RuntimeError(f"CDP error: {result['error']}")
        return result.get("result", {})

    async def evaluate(self, expression: str) -> Any:
        """Execute JavaScript and return result."""
        result = await self.send("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": True,
        })
        remote = result.get("result", {})
        if remote.get("type") == "undefined":
            return None
        return remote.get("value", remote.get("description", ""))

    async def navigate(self, url: str) -> None:
        """Navigate to URL and wait for load."""
        await self.send("Page.enable")
        await self.send("Page.navigate", {"url": url})
        await asyncio.sleep(1.5)

    async def get_accessibility_tree(self) -> str:
        """Get page accessibility tree — structured, token-efficient alternative to screenshots."""
        result = await self.send("Accessibility.getFullAXTree")
        nodes = result.get("nodes", [])
        lines = []
        for node in nodes[:200]:
            role = node.get("role", {}).get("value", "")
            name = node.get("name", {}).get("value", "")
            value = node.get("value", {}).get("value", "")
            if not role or role in ("generic", "none", "InlineTextBox"):
                continue
            parts = [f"[{role}]"]
            if name:
                parts.append(f'"{name}"')
            if value:
                parts.append(f"value={value}")
            lines.append(" ".join(parts))
        return "\n".join(lines)

    async def list_tabs(self) -> list[dict]:
        """List all open Chrome tabs."""
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"http://localhost:{self.port}/json")
            tabs = resp.json()
        return [
            {"id": t["id"], "title": t.get("title", ""), "url": t.get("url", ""), "type": t.get("type", "")}
            for t in tabs if t.get("type") == "page"
        ]

    async def switch_tab(self, tab_id: str) -> None:
        """Switch to a specific tab by ID. Reconnects websocket."""
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"http://localhost:{self.port}/json")
            tabs = resp.json()
        target = None
        for tab in tabs:
            if tab["id"] == tab_id:
                target = tab
                break
        if not target:
            raise ValueError(f"Tab {tab_id} not found")
        if self._ws:
            await self._ws.close()
            self._ws = None
        import websockets
        self._ws = await websockets.connect(target["webSocketDebuggerUrl"], max_size=10 * 1024 * 1024)
        asyncio.create_task(self._listen())

    async def close(self) -> None:
        """Close websocket connection."""
        if self._ws:
            await self._ws.close()
            self._ws = None
