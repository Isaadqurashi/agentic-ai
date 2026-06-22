from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import sys
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_ROOT = PROJECT_ROOT / "config"


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data


@lru_cache(maxsize=8)
def load_agents_config(path: str | Path | None = None) -> dict[str, Any]:
    return _load_yaml(Path(path) if path else CONFIG_ROOT / "agents.yaml")


@lru_cache(maxsize=8)
def load_mcp_servers_config(path: str | Path | None = None) -> dict[str, Any]:
    return _load_yaml(Path(path) if path else CONFIG_ROOT / "mcp_servers.yaml")


def get_agent_config(agent_id: str) -> dict[str, Any]:
    for agent in load_agents_config().get("agents", []):
        if agent.get("id") == agent_id:
            return dict(agent)
    raise KeyError(f"Unknown agent id: {agent_id}")


def iter_specialist_configs() -> list[dict[str, Any]]:
    return [
        dict(agent)
        for agent in load_agents_config().get("agents", [])
        if agent.get("id") != "orchestrator" and agent.get("role") != "orchestrator"
    ]


def mcp_client_config_for(agent_cfg: dict[str, Any]) -> dict[str, Any]:
    registry = load_mcp_servers_config().get("servers", {})
    selected: dict[str, Any] = {}
    for server_name in agent_cfg.get("mcp_servers", []):
        if server_name not in registry:
            raise KeyError(f"Agent {agent_cfg.get('id')} references unknown MCP server {server_name}")
        server_cfg = dict(registry[server_name])
        if server_cfg.get("command") == "python":
            server_cfg["command"] = sys.executable
        selected[server_name] = server_cfg
    return selected
