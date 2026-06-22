from __future__ import annotations

import os

import pytest

from agentmesh.graphs.agent_graph_factory import _assert_no_delegate_tools, build_agent_graph


class FakeTool:
    def __init__(self, name: str) -> None:
        self.name = name


@pytest.mark.asyncio
async def test_dry_run_agent_build_requires_no_key(monkeypatch) -> None:
    monkeypatch.setenv("DRY_RUN", "true")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    graph = await build_agent_graph("researcher")
    result = await graph.ainvoke({"messages": [{"role": "user", "content": "hello"}]})
    assert "messages" in result
    assert os.getenv("OPENAI_API_KEY") is None


def test_specialist_delegate_tools_are_rejected() -> None:
    with pytest.raises(ValueError):
        _assert_no_delegate_tools("researcher", [FakeTool("delegate_to_coder")])
    _assert_no_delegate_tools("orchestrator", [FakeTool("delegate_to_coder")])
