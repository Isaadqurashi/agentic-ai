from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse

from agentmesh.a2a.client import send_message


ORCHESTRATOR_URL = "http://127.0.0.1:9100"
STATIC_DIR = Path(__file__).resolve().parent / "static"


app = FastAPI(title="Agentmesh Web")


def _sse_event(data: str, event: str | None = None) -> str:
    event_line = f"event: {event}\n" if event else ""
    return f"{event_line}data: {json.dumps(data)}\n\n"


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/chat")
async def chat(q: str):
    async def events():
        try:
            text = await send_message(os.getenv("AGENTMESH_ORCHESTRATOR_URL", ORCHESTRATOR_URL), q)
            yield _sse_event(text)
        except Exception as exc:
            yield _sse_event(str(exc), event="agent-error")

    return StreamingResponse(events(), media_type="text/event-stream")


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("AGENTMESH_WEB_PORT", "8080")))


if __name__ == "__main__":
    main()
