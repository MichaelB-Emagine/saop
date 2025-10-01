# saop_core/llm/client.py
from __future__ import annotations
from typing import Any, Dict
import httpx


class LLMClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

    async def responses(
        self, system: str, user: str, model: str, temperature: float = 0.1
    ) -> Dict[str, Any]:
        payload = {
            "model": model,
            "temperature": temperature,
            "input": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(
                f"{self.base_url}/responses", headers=self._headers(), json=payload
            )
            r.raise_for_status()
            data = r.json()
            # Normalize
            try:
                content = data["output"][0]["content"][0]["text"]
            except Exception:
                content = str(data)
            usage = data.get("usage", {}) or data.get("usage_metadata", {})
            return {"content": content, "usage_metadata": usage}
