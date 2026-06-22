from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
import os
from threading import Lock
from typing import Any


DEFAULT_PRICE_TABLE_USD_PER_1M_TOKENS: dict[str, dict[str, Decimal]] = {
    "gpt-4o-mini": {"input": Decimal("0.15"), "output": Decimal("0.60")},
}


class BudgetExceeded(RuntimeError):
    """Raised when the configured session budget is exceeded."""


@dataclass(frozen=True)
class UsageRecord:
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: Decimal
    source: str = "llm"


@dataclass
class SessionCostTracker:
    max_usd: Decimal = field(default_factory=lambda: Decimal(os.getenv("MAX_SESSION_USD", "1.00")))
    price_table: dict[str, dict[str, Decimal]] = field(
        default_factory=lambda: {k: dict(v) for k, v in DEFAULT_PRICE_TABLE_USD_PER_1M_TOKENS.items()}
    )

    def __post_init__(self) -> None:
        self._records: list[UsageRecord] = []
        self._lock = Lock()

    @property
    def total_usd(self) -> Decimal:
        with self._lock:
            return sum((record.cost_usd for record in self._records), Decimal("0"))

    @property
    def records(self) -> list[UsageRecord]:
        with self._lock:
            return list(self._records)

    def estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> Decimal:
        prices = self.price_table.get(model) or self.price_table.get(model.split(":")[-1])
        if not prices:
            prices = {"input": Decimal("1.00"), "output": Decimal("1.00")}
        input_cost = Decimal(input_tokens) * prices["input"] / Decimal(1_000_000)
        output_cost = Decimal(output_tokens) * prices["output"] / Decimal(1_000_000)
        return input_cost + output_cost

    def assert_budget_available(self) -> None:
        if self.total_usd >= self.max_usd:
            raise BudgetExceeded(
                f"Session budget reached: ${self.total_usd:.6f} >= ${self.max_usd:.2f}. "
                "No further OpenAI calls will be made."
            )

    def record_usage(
        self,
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        source: str = "llm",
    ) -> UsageRecord:
        cost = self.estimate_cost(model, input_tokens, output_tokens)
        record = UsageRecord(model=model, input_tokens=input_tokens, output_tokens=output_tokens, cost_usd=cost, source=source)
        with self._lock:
            projected = sum((item.cost_usd for item in self._records), Decimal("0")) + cost
            if projected > self.max_usd:
                raise BudgetExceeded(
                    f"Session budget exceeded: projected ${projected:.6f} > ${self.max_usd:.2f}. "
                    "No further OpenAI calls will be made."
                )
            self._records.append(record)
        return record

    def reset(self) -> None:
        with self._lock:
            self._records.clear()


GLOBAL_TRACKER = SessionCostTracker()


def get_tracker() -> SessionCostTracker:
    return GLOBAL_TRACKER


def record_usage_from_metadata(model: str, usage_metadata: dict[str, Any] | None, source: str = "llm") -> UsageRecord | None:
    if not usage_metadata:
        return None
    input_tokens = int(
        usage_metadata.get("input_tokens")
        or usage_metadata.get("prompt_tokens")
        or usage_metadata.get("input_token_count")
        or 0
    )
    output_tokens = int(
        usage_metadata.get("output_tokens")
        or usage_metadata.get("completion_tokens")
        or usage_metadata.get("output_token_count")
        or 0
    )
    return GLOBAL_TRACKER.record_usage(model=model, input_tokens=input_tokens, output_tokens=output_tokens, source=source)
