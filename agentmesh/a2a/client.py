from __future__ import annotations

from typing import Any
from uuid import uuid4

import httpx


async def fetch_agent_card(base_url: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(base_url.rstrip("/") + "/.well-known/agent-card.json")
        response.raise_for_status()
        return response.json()


async def send_message(base_url: str, text: str, task_id: str | None = None) -> str:
    request_id = str(uuid4())
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            base_url.rstrip("/") + "/",
            json={
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "message/send",
                "params": {"task_id": task_id or request_id, "text": text},
            },
        )
        response.raise_for_status()
        payload = response.json()
    if payload.get("error"):
        error = payload["error"]
        if isinstance(error, dict):
            raise RuntimeError(f"{error.get('type', 'A2AError')}: {error.get('message', error)}")
        raise RuntimeError(error)
    result = payload.get("result", {})
    if "text" in result:
        return str(result["text"])
    parts = (result.get("artifact") or {}).get("parts") or []
    return "\n".join(str(part.get("text", "")) for part in parts if isinstance(part, dict))
