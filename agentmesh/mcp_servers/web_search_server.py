from __future__ import annotations

from typing import Any


def search_web(query: str, max_results: int = 5) -> list[dict[str, str]]:
    if not query.strip():
        raise ValueError("query must not be empty")
    max_results = max(1, min(int(max_results), 10))

    from ddgs import DDGS

    results: list[dict[str, str]] = []
    with DDGS() as ddgs:
        for item in ddgs.text(query, max_results=max_results):
            results.append(
                {
                    "title": str(item.get("title", "")),
                    "url": str(item.get("href") or item.get("url") or ""),
                    "snippet": str(item.get("body") or item.get("snippet") or ""),
                }
            )
    return results


def _build_server() -> Any:
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("web_search_server")
    mcp.tool()(search_web)
    return mcp


def main() -> None:
    _build_server().run()


if __name__ == "__main__":
    main()
