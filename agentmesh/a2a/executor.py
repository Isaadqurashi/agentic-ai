from __future__ import annotations

import os
from typing import Any
from uuid import uuid4


def recursion_limit() -> int:
    return int(os.getenv("AGENTMESH_RECURSION_LIMIT", "12"))


def extract_final_text(result: Any) -> str:
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        messages = result.get("messages")
        if messages:
            last = messages[-1]
            if isinstance(last, dict):
                return str(last.get("content", ""))
            return str(getattr(last, "content", last))
        if "content" in result:
            return str(result["content"])
    return str(result)


class GraphAgentExecutor:
    def __init__(self, graph: Any) -> None:
        self.graph = graph

    async def execute_text(self, text: str, task_id: str | None = None) -> str:
        task_id = task_id or str(uuid4())
        result = await self.graph.ainvoke(
            {"messages": [{"role": "user", "content": text}]},
            config={"configurable": {"thread_id": task_id}, "recursion_limit": recursion_limit()},
        )
        return extract_final_text(result)
