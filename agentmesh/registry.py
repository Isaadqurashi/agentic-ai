from __future__ import annotations

from typing import Any

from agentmesh.a2a.client import fetch_agent_card
from agentmesh.utils.config_loader import iter_specialist_configs


async def discover_specialist_cards() -> dict[str, dict[str, Any]]:
    cards: dict[str, dict[str, Any]] = {}
    for cfg in iter_specialist_configs():
        base_url = f"http://127.0.0.1:{int(cfg['port'])}"
        cards[cfg["id"]] = await fetch_agent_card(base_url)
    return cards
