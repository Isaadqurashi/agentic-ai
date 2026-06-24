from __future__ import annotations

import traceback
from typing import Any
from uuid import uuid4

from agentmesh.a2a.cards import build_agent_card
from agentmesh.a2a.executor import GraphAgentExecutor
from agentmesh.utils.cost_tracker import get_tracker


def build_a2a_app(graph: Any, agent_cfg: dict[str, Any]) -> Any:
    from fastapi import Body, FastAPI
 
    card = build_agent_card(agent_cfg)
    executor = GraphAgentExecutor(graph)
    app = FastAPI(title=card["name"])

    @app.get("/.well-known/agent-card.json")
    async def agent_card() -> dict[str, Any]:
        return card

    @app.get("/cost")
    async def cost() -> dict[str, str]:
        tracker = get_tracker()
        return {"total_usd": f"{tracker.total_usd:.6f}", "max_usd": f"{tracker.max_usd:.2f}"}

    @app.post("/")
    async def json_rpc(request: dict[str, Any] = Body(...)) -> dict[str, Any]:
        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params") or {}
        if method not in {"message/send", "tasks/send", "send_message"}:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Unsupported method: {method}"},
            }
        text = _extract_text(params)
        task_id = str(params.get("task_id") or params.get("id") or uuid4())
        try:
            result = await executor.execute_text(text, task_id=task_id)
        except Exception as exc:
            traceback.print_exc()
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32000, "message": str(exc), "type": type(exc).__name__},
            }
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "task_id": task_id,
                "status": "completed",
                "artifact": {"parts": [{"type": "text", "text": result}]},
                "text": result,
            },
        }

    return app


def _extract_text(params: dict[str, Any]) -> str:
    if "text" in params:
        return str(params["text"])
    message = params.get("message")
    if isinstance(message, str):
        return message
    if isinstance(message, dict):
        if "content" in message:
            return str(message["content"])
        parts = message.get("parts") or []
        for part in parts:
            if isinstance(part, dict) and part.get("type") == "text":
                return str(part.get("text", ""))
    return str(params)
