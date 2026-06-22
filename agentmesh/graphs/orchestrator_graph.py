from __future__ import annotations

from typing import Any

from agentmesh.a2a.delegate_tool import build_delegate_tool
from agentmesh.graphs.agent_graph_factory import DryRunCompiledGraph, _load_mcp_tools
from agentmesh.graphs.checkpoints import get_async_checkpointer
from agentmesh.llm.models import get_chat_model
from agentmesh.registry import discover_specialist_cards
from agentmesh.utils.config_loader import get_agent_config


async def build_orchestrator_graph(agent_cards: dict[str, dict[str, Any]] | None = None) -> Any:
    cfg = get_agent_config("orchestrator")
    own_tools = await _load_mcp_tools(cfg)
    cards = agent_cards if agent_cards is not None else await discover_specialist_cards()
    delegate_tools = [build_delegate_tool(agent_id, card) for agent_id, card in cards.items()]
    tools = own_tools + delegate_tools
    model = get_chat_model(cfg)

    try:
        from langgraph.graph import END, MessagesState, StateGraph
        from langgraph.prebuilt import ToolNode, tools_condition
    except Exception:
        return DryRunCompiledGraph("orchestrator", cfg)

    llm_with_tools = model.bind_tools(tools)

    async def assistant(state: MessagesState) -> dict[str, Any]:
        response = await llm_with_tools.ainvoke(
            [{"role": "system", "content": cfg.get("system_prompt", "")}] + list(state["messages"])
        )
        return {"messages": [response]}

    graph = StateGraph(MessagesState)
    graph.add_node("assistant", assistant)
    graph.add_node("tools", ToolNode(tools))
    graph.set_entry_point("assistant")
    graph.add_conditional_edges("assistant", tools_condition, {"tools": "tools", END: END})
    graph.add_edge("tools", "assistant")

    compile_kwargs: dict[str, Any] = {}
    checkpointer = await get_async_checkpointer("orchestrator")
    if checkpointer is not None:
        compile_kwargs["checkpointer"] = checkpointer
    return graph.compile(**compile_kwargs)
