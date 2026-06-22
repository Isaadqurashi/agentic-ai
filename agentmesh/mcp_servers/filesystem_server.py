from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def workspace_root() -> Path:
    root = Path(os.getenv("AGENTMESH_WORKSPACE_ROOT", ".")).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def resolve_workspace_path(path: str) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        raise ValueError("absolute paths are not allowed")
    resolved = (workspace_root() / candidate).resolve()
    root = workspace_root()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("path escapes the configured workspace root") from exc
    return resolved


def read_file(path: str) -> str:
    resolved = resolve_workspace_path(path)
    if not resolved.is_file():
        raise FileNotFoundError(path)
    return resolved.read_text(encoding="utf-8")


def write_file(path: str, content: str) -> str:
    resolved = resolve_workspace_path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content, encoding="utf-8")
    return str(resolved.relative_to(workspace_root()))


def list_dir(path: str = ".") -> list[dict[str, Any]]:
    resolved = resolve_workspace_path(path)
    if not resolved.is_dir():
        raise NotADirectoryError(path)
    root = workspace_root()
    entries: list[dict[str, Any]] = []
    for item in sorted(resolved.iterdir(), key=lambda entry: entry.name.lower()):
        entries.append(
            {
                "name": item.name,
                "path": str(item.relative_to(root)),
                "type": "directory" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else None,
            }
        )
    return entries


def _build_server() -> Any:
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("filesystem_server")
    mcp.tool()(read_file)
    mcp.tool()(write_file)
    mcp.tool()(list_dir)
    return mcp


def main() -> None:
    _build_server().run()


if __name__ == "__main__":
    main()
