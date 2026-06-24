from __future__ import annotations

import hashlib
import hmac
import json
import os
from typing import Any
 

def sign_card(card: dict[str, Any]) -> str:
    secret = os.getenv("AGENTMESH_CARD_SIGNING_SECRET", "agentmesh-dev-signing-key")
    payload = json.dumps({k: v for k, v in card.items() if k != "signature"}, sort_keys=True).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def build_agent_card(agent_cfg: dict[str, Any], base_url: str | None = None) -> dict[str, Any]:
    port = int(agent_cfg["port"])
    url = base_url or f"http://127.0.0.1:{port}/"
    skills = agent_cfg.get("skills") or [
        {
            "id": agent_cfg["id"],
            "name": agent_cfg.get("name", agent_cfg["id"]),
            "description": agent_cfg.get("description", ""),
        }
    ]
    card = {
        "protocolVersion": "1.0",
        "name": agent_cfg.get("name", agent_cfg["id"]),
        "description": agent_cfg.get("description", ""),
        "url": url,
        "version": "0.1.0",
        "capabilities": {"streaming": False, "pushNotifications": False},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "skills": skills,
        "metadata": {"agent_id": agent_cfg["id"], "model": agent_cfg.get("model")},
    }
    card["signature"] = sign_card(card)
    return card
