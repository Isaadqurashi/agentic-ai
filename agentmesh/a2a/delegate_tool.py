from __future__ import annotations

from typing import Any

from agentmesh.a2a.client import send_message


class SimpleAsyncTool:
    def __init__(self, name: str, description: str, coroutine: Any) -> None:
        self.name = name
        self.description = description
        self.coroutine = coroutine

    async def ainvoke(self, task: str) -> str:
        return await self.coroutine(task)


def _description_from_card(card: dict[str, Any]) -> str:
    skills = card.get("skills") or []
    skill_text = "; ".join(
        f"{skill.get('name', skill.get('id', 'skill'))}: {skill.get('description', '')}" for skill in skills
    )
    return f"{card.get('description', '')} Skills: {skill_text}".strip()


def build_delegate_tool(agent_id: str, card: dict[str, Any]) -> Any:
    name = f"delegate_to_{agent_id}"
    description = _description_from_card(card)
    url = card["url"]

    async def _delegate(task: str) -> str:
        """Delegate a task to a remote A2A specialist agent."""
        return await send_message(url, task)

    try:
        from langchain_core.tools import StructuredTool
    except Exception:
        return SimpleAsyncTool(name=name, description=description, coroutine=_delegate)

    return StructuredTool.from_function(
        coroutine=_delegate,
        name=name,
        description=description,
    )
