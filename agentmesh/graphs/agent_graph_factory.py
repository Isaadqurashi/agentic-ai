from __future__ import annotations

import importlib
import inspect
from typing import Any

from agentmesh.graphs.checkpoints import get_async_checkpointer
from agentmesh.llm.models import get_chat_model
from agentmesh.utils.config_loader import get_agent_config, mcp_client_config_for


class DryRunCompiledGraph:
    def __init__(self, agent_id: str, cfg: dict[str, Any]) -> None:
        self.agent_id = agent_id
        self.cfg = cfg

    async def ainvoke(self, state: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]:
        content = _last_message_content(state.get("messages", []))
        return {"messages": [{"role": "assistant", "content": f"[DRY_RUN:{self.agent_id}] {content}"}]}

    def invoke(self, state: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]:
        content = _last_message_content(state.get("messages", []))
        return {"messages": [{"role": "assistant", "content": f"[DRY_RUN:{self.agent_id}] {content}"}]}


def _last_message_content(messages: Any) -> str:
    if not messages:
        return ""
    last = messages[-1]
    if isinstance(last, dict):
        return str(last.get("content", ""))
    return str(getattr(last, "content", last))


def _assert_no_delegate_tools(agent_id: str, tools: list[Any]) -> None:
    if agent_id == "orchestrator":
        return
    names = [getattr(tool, "name", "") for tool in tools]
    offenders = [name for name in names if name.startswith("delegate_to_")]
    if offenders:
        raise ValueError(f"Specialist agent {agent_id} cannot be given delegation tools: {offenders}")


async def _load_mcp_tools(agent_cfg: dict[str, Any]) -> list[Any]:
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
    except Exception:
        return []
    client = MultiServerMCPClient(mcp_client_config_for(agent_cfg))
    return list(await client.get_tools())


def _load_custom_graph(builder_ref: str) -> Any:
    module_name, function_name = builder_ref.split(":", 1)
    module = importlib.import_module(module_name)
    return getattr(module, function_name)


async def build_agent_graph(agent_id: str) -> Any:
    agent_cfg = get_agent_config(agent_id)
    model = get_chat_model(agent_cfg)
    tools = await _load_mcp_tools(agent_cfg)
    _assert_no_delegate_tools(agent_id, tools)

    if agent_cfg.get("custom_graph"):
        builder = _load_custom_graph(agent_cfg["custom_graph"])
        return builder(model, tools, agent_cfg)

    try:
        from langchain.agents import create_agent
    except Exception:
        return DryRunCompiledGraph(agent_id, agent_cfg)

    checkpointer = await get_async_checkpointer(agent_id)
    kwargs: dict[str, Any] = {}
    if checkpointer is not None:
        kwargs["checkpointer"] = checkpointer
    prompt_param = "prompt" if "prompt" in inspect.signature(create_agent).parameters else "system_prompt"
    kwargs[prompt_param] = agent_cfg.get("system_prompt", "")
    return create_agent(
        model=model,
        tools=tools,
        **kwargs,
    )


def build_agent_graph_sync(agent_id: str) -> Any:
    import asyncio

    return asyncio.run(build_agent_graph(agent_id))
