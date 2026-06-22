from __future__ import annotations

import ast
import subprocess
import sys
from typing import Any


ALLOWED_IMPORTS = {"math", "statistics", "json", "datetime"}
BLOCKED_NAMES = {"open", "exec", "eval", "compile", "__import__", "input", "breakpoint"}
BLOCKED_IMPORTS = {"os", "sys", "subprocess", "socket", "pathlib", "shutil", "requests", "httpx"}


def validate_python(code: str) -> None:
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root not in ALLOWED_IMPORTS or root in BLOCKED_IMPORTS:
                    raise ValueError(f"import not allowed: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root not in ALLOWED_IMPORTS or root in BLOCKED_IMPORTS:
                raise ValueError(f"import not allowed: {node.module}")
        elif isinstance(node, ast.Name) and node.id in BLOCKED_NAMES:
            raise ValueError(f"name not allowed: {node.id}")
        elif isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise ValueError("dunder attribute access is not allowed")


def run_python(code: str, timeout_seconds: int = 5) -> dict[str, Any]:
    validate_python(code)
    completed = subprocess.run(
        [sys.executable, "-I", "-c", code],
        text=True,
        capture_output=True,
        timeout=max(1, min(int(timeout_seconds), 10)),
        check=False,
    )
    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _build_server() -> Any:
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("python_exec_server")
    mcp.tool()(run_python)
    return mcp


def main() -> None:
    _build_server().run()


if __name__ == "__main__":
    main()
