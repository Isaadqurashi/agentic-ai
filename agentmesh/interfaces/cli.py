from __future__ import annotations

import asyncio
from decimal import Decimal
import os

import httpx
from rich.console import Console
from rich.prompt import Prompt

from agentmesh.a2a.client import send_message


ORCHESTRATOR_URL = "http://127.0.0.1:9100"


async def fetch_remote_cost(base_url: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(base_url.rstrip("/") + "/cost")
            response.raise_for_status()
            payload = response.json()
            return str(payload.get("total_usd", "unknown"))
    except Exception:
        return "unknown"


async def chat_loop() -> None:
    console = Console()
    console.print("Agentmesh CLI. Type /exit to quit.")
    while True:
        text = Prompt.ask("[bold]you[/bold]")
        if text.strip() in {"/exit", "/quit"}:
            return
        orchestrator_url = os.getenv("AGENTMESH_ORCHESTRATOR_URL", ORCHESTRATOR_URL)
        try:
            response = await send_message(orchestrator_url, text)
            console.print(f"[bold]agentmesh[/bold] {response}")
        except Exception as exc:
            console.print(f"[bold red]agentmesh error[/bold red] {exc}")
        total = await fetch_remote_cost(orchestrator_url)
        console.print(
            f"[dim]session cost: ${Decimal(total):.6f}[/dim]" if total != "unknown" else "[dim]session cost: unknown[/dim]"
        )


def main() -> None:
    asyncio.run(chat_loop())


if __name__ == "__main__":
    main()
