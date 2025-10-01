# saop_core/mcp/client.py
from __future__ import annotations
from typing import Any, Dict
import httpx


class MCPClient:
    def __init__(self, base_url: str, bearer_token: str = ""):
        self.base_url = base_url.rstrip("/")  # e.g. http://mcp:9000/mcp
        self.bearer = bearer_token

    def _headers(self) -> Dict[str, str]:
        h = {
            "Content-Type": "application/json",
            "Accept": "*/*",  # be permissive; avoids 406 differences across builds
        }
        if self.bearer:
            h["Authorization"] = f"Bearer {self.bearer}"
        return h

    async def call_tool(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        payload = {"method": "tools/call", "params": {"tool": name, "args": args}}
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(self.base_url, headers=self._headers(), json=payload)
            # if server streams NDJSON/SSE as a single JSON object, this still works;
            # if not JSON, surface the raw text to help debug.
            if 200 <= r.status_code < 300:
                try:
                    return r.json()
                except Exception:
                    return {"raw": r.text}
            raise RuntimeError(
                f"MCP call_tool('{name}') failed: {r.status_code} {r.text[:200]}"
            )
