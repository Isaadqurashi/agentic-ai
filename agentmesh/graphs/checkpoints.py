from __future__ import annotations

import os
from pathlib import Path
from typing import Any


_OPEN_CHECKPOINTERS: list[Any] = []
_OPEN_ASYNC_CHECKPOINTERS: list[Any] = []

 
def checkpoint_path(agent_id: str) -> Path:
    data_dir = Path(os.getenv("AGENTMESH_DATA_DIR", ".agentmesh_data")).resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / f"{agent_id}.sqlite3"


def get_checkpointer(agent_id: str) -> Any | None:
    if os.getenv("AGENTMESH_ENABLE_SQLITE_CHECKPOINTS", "false").lower() not in {"1", "true", "yes", "on"}:
        return None
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
    except Exception:
        return None
    saver = SqliteSaver.from_conn_string(str(checkpoint_path(agent_id)))
    if hasattr(saver, "__enter__"):
        context_manager = saver
        saver = context_manager.__enter__()
        _OPEN_CHECKPOINTERS.append(context_manager)
    return saver


async def get_async_checkpointer(agent_id: str) -> Any | None:
    if os.getenv("AGENTMESH_ENABLE_SQLITE_CHECKPOINTS", "false").lower() not in {"1", "true", "yes", "on"}:
        return None
    try:
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    except Exception:
        return None
    saver = AsyncSqliteSaver.from_conn_string(str(checkpoint_path(agent_id)))
    if hasattr(saver, "__aenter__"):
        context_manager = saver
        saver = await context_manager.__aenter__()
        _OPEN_ASYNC_CHECKPOINTERS.append(context_manager)
    return saver
