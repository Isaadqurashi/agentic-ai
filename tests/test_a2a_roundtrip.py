from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
httpx = pytest.importorskip("httpx")

from agentmesh.a2a.server_factory import build_a2a_app


class EchoGraph:
    async def ainvoke(self, state, config=None):
        text = state["messages"][-1]["content"]
        return {"messages": [{"role": "assistant", "content": f"echo: {text}"}]}


@pytest.mark.asyncio
async def test_card_fetch_and_message_roundtrip() -> None:
    app = build_a2a_app(
        EchoGraph(),
        {
            "id": "echo",
            "name": "Echo Agent",
            "description": "Echoes text.",
            "port": 9999,
            "model": "gpt-4o-mini",
        },
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        card = (await client.get("/.well-known/agent-card.json")).json()
        assert card["metadata"]["agent_id"] == "echo"
        assert card["signature"]
        response = await client.post(
            "/",
            json={"jsonrpc": "2.0", "id": "1", "method": "message/send", "params": {"text": "ping"}},
        )
    payload = response.json()
    assert payload["result"]["text"] == "echo: ping"
