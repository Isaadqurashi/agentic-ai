from __future__ import annotations

import argparse
import asyncio

import uvicorn

from agentmesh.a2a.server_factory import build_a2a_app
from agentmesh.graphs.agent_graph_factory import build_agent_graph
from agentmesh.graphs.orchestrator_graph import build_orchestrator_graph
from agentmesh.utils.config_loader import get_agent_config


async def _build_app(agent_id: str):
    cfg = get_agent_config(agent_id)
    graph = await build_orchestrator_graph() if agent_id == "orchestrator" else await build_agent_graph(agent_id)
    checkpointer = getattr(graph, "checkpointer", None)
    print(f"agentmesh graph ready: {agent_id} checkpointer={type(checkpointer).__module__}.{type(checkpointer).__name__}", flush=True)
    return build_a2a_app(graph, cfg)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("agent_id")
    args = parser.parse_args()
    cfg = get_agent_config(args.agent_id)
    app = asyncio.run(_build_app(args.agent_id))
    uvicorn.run(app, host="127.0.0.1", port=int(cfg["port"]))


if __name__ == "__main__":
    main()
