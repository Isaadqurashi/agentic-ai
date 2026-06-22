from __future__ import annotations

import pytest

from agentmesh.a2a.delegate_tool import build_delegate_tool
from agentmesh.graphs.agent_graph_factory import _assert_no_delegate_tools


@pytest.mark.asyncio
async def test_delegate_tool_uses_remote_card_url(monkeypatch) -> None:
    calls = []

    async def fake_send_message(url: str, text: str, task_id=None) -> str:
        calls.append((url, text))
        return "specialist result"

    monkeypatch.setattr("agentmesh.a2a.delegate_tool.send_message", fake_send_message)
    tool = build_delegate_tool(
        "coder",
        {
            "url": "http://127.0.0.1:9102/",
            "description": "Writes code.",
            "skills": [{"name": "Code", "description": "Code tasks."}],
        },
    )
    if hasattr(tool, "ainvoke"):
        result = await tool.ainvoke("fix the bug")
    else:
        result = await tool.coroutine("fix the bug")
    assert result == "specialist result"
    assert calls == [("http://127.0.0.1:9102/", "fix the bug")]


def test_specialist_never_gets_delegate_tools() -> None:
    class Tool:
        name = "delegate_to_researcher"

    with pytest.raises(ValueError):
        _assert_no_delegate_tools("coder", [Tool()])
