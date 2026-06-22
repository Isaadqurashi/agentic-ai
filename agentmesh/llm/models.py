from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from agentmesh.utils.cost_tracker import get_tracker, record_usage_from_metadata


def load_env_file(override: bool = True) -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().lstrip("\ufeff")
        value = value.strip().strip('"').strip("'")
        if override or key not in os.environ:
            os.environ[key] = value


def is_dry_run() -> bool:
    return os.getenv("DRY_RUN", "false").lower() in {"1", "true", "yes", "on"}


try:
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.messages import AIMessage, BaseMessage
    from langchain_core.outputs import ChatGeneration, ChatResult
    from pydantic import Field

    class DryRunChatModel(BaseChatModel):
        """Deterministic chat model used for tests and no-spend smoke checks."""

        model_name: str = "dry-run"
        bound_tools: list[Any] = Field(default_factory=list)

        @property
        def _llm_type(self) -> str:
            return "agentmesh-dry-run"

        def bind_tools(self, tools: list[Any], **kwargs: Any) -> "DryRunChatModel":
            return self.model_copy(update={"bound_tools": list(tools)})

        def _response_text(self, messages: list[BaseMessage]) -> str:
            last = messages[-1].content if messages else ""
            names = ", ".join(getattr(tool, "name", repr(tool)) for tool in self.bound_tools)
            suffix = f" Available tools: {names}." if names else ""
            return f"[DRY_RUN:{self.model_name}] {last}{suffix}"

        def _generate(
            self,
            messages: list[BaseMessage],
            stop: list[str] | None = None,
            run_manager: Any | None = None,
            **kwargs: Any,
        ) -> ChatResult:
            message = AIMessage(
                content=self._response_text(messages),
                usage_metadata={"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
            )
            return ChatResult(generations=[ChatGeneration(message=message)])

        async def _agenerate(
            self,
            messages: list[BaseMessage],
            stop: list[str] | None = None,
            run_manager: Any | None = None,
            **kwargs: Any,
        ) -> ChatResult:
            return self._generate(messages, stop=stop, run_manager=run_manager, **kwargs)

except Exception:  # pragma: no cover - used only when LangChain is not installed.

    class DryRunChatModel:
        def __init__(self, model_name: str = "dry-run", bound_tools: list[Any] | None = None) -> None:
            self.model_name = model_name
            self.bound_tools = bound_tools or []

        def bind_tools(self, tools: list[Any], **kwargs: Any) -> "DryRunChatModel":
            return DryRunChatModel(self.model_name, list(tools))

        async def ainvoke(self, messages: Any, **kwargs: Any) -> Any:
            return {"content": f"[DRY_RUN:{self.model_name}] {messages}"}

        def invoke(self, messages: Any, **kwargs: Any) -> Any:
            return {"content": f"[DRY_RUN:{self.model_name}] {messages}"}


try:
    from langchain_core.callbacks import BaseCallbackHandler
except Exception:  # pragma: no cover
    BaseCallbackHandler = object  # type: ignore[misc,assignment]


class UsageTrackingCallback(BaseCallbackHandler):
    def __init__(self, model_name: str) -> None:
        super().__init__()
        self.model_name = model_name

    def on_llm_start(self, *args: Any, **kwargs: Any) -> None:
        get_tracker().assert_budget_available()

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        llm_output = getattr(response, "llm_output", None) or {}
        usage = llm_output.get("token_usage") or llm_output.get("usage")
        if usage:
            record_usage_from_metadata(self.model_name, usage)
            return

        for generations in getattr(response, "generations", []) or []:
            for generation in generations:
                message = getattr(generation, "message", None)
                usage_metadata = getattr(message, "usage_metadata", None)
                if usage_metadata:
                    record_usage_from_metadata(self.model_name, usage_metadata)
                    return


def get_chat_model(agent_cfg: dict[str, Any]) -> Any:
    if "DRY_RUN" in os.environ and is_dry_run():
        return DryRunChatModel(model_name=agent_cfg["model"])

    load_env_file()
    model_name = agent_cfg["model"]
    if is_dry_run():
        return DryRunChatModel(model_name=model_name)

    if not os.getenv("OPENAI_API_KEY") and not os.getenv("OPENAI_ADMIN_KEY"):
        raise RuntimeError(
            "DRY_RUN=false requires OPENAI_API_KEY. Set it in PowerShell with "
            "`$env:OPENAI_API_KEY = \"sk-...\"` or add it to .env."
        )
    api_key = os.getenv("OPENAI_API_KEY", "")
    if api_key.startswith("Sk-"):
        raise RuntimeError(
            "OPENAI_API_KEY starts with `Sk-`, but OpenAI API keys are case-sensitive and should start with `sk-`. "
            "Fix the key in .env or create a new key at https://platform.openai.com/api-keys."
        )

    get_tracker().assert_budget_available()

    from langchain.chat_models import init_chat_model

    return init_chat_model(
        f"openai:{model_name}",
        temperature=agent_cfg.get("temperature", 0.2),
        callbacks=[UsageTrackingCallback(model_name)],
    )
