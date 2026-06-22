from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse

from agentmesh.a2a.client import send_message


ORCHESTRATOR_URL = "http://127.0.0.1:9100"
STATIC_DIR = Path(__file__).resolve().parent / "static"


app = FastAPI(title="Agentmesh Web")


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/chat")
async def chat(q: str):
    async def events():
        try:
            text = await send_message(os.getenv("AGENTMESH_ORCHESTRATOR_URL", ORCHESTRATOR_URL), q)
            yield f"data: {text}\n\n"
        except Exception as exc:
            yield f"event: error\ndata: {exc}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("AGENTMESH_WEB_PORT", "8080")))


if __name__ == "__main__":
    main()
