from __future__ import annotations

from decimal import Decimal

import pytest

from agentmesh.a2a.executor import GraphAgentExecutor
from agentmesh.utils.cost_tracker import BudgetExceeded, SessionCostTracker


def test_budget_cutoff_triggers() -> None:
    tracker = SessionCostTracker(max_usd=Decimal("0.000001"))
    with pytest.raises(BudgetExceeded):
        tracker.record_usage("gpt-4o-mini", input_tokens=1000, output_tokens=1000)


def test_usage_recording_stays_under_budget() -> None:
    tracker = SessionCostTracker(max_usd=Decimal("1.00"))
    record = tracker.record_usage("gpt-4o-mini", input_tokens=100, output_tokens=50)
    assert record.cost_usd > 0
    assert tracker.total_usd == record.cost_usd


class CapturingGraph:
    def __init__(self) -> None:
        self.config = None

    async def ainvoke(self, state, config=None):
        self.config = config
        return {"messages": [{"role": "assistant", "content": "done"}]}


@pytest.mark.asyncio
async def test_recursion_limit_is_passed(monkeypatch) -> None:
    monkeypatch.setenv("AGENTMESH_RECURSION_LIMIT", "7")
    graph = CapturingGraph()
    executor = GraphAgentExecutor(graph)
    result = await executor.execute_text("hello", task_id="test-task")
    assert result == "done"
    assert graph.config["recursion_limit"] == 7
    assert graph.config["configurable"]["thread_id"] == "test-task"
