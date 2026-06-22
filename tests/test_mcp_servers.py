from __future__ import annotations

import pytest

from agentmesh.mcp_servers.filesystem_server import list_dir, read_file, resolve_workspace_path, write_file
from agentmesh.mcp_servers.memory_server import recall, remember
from agentmesh.mcp_servers.python_exec_server import run_python, validate_python


def test_filesystem_server_rejects_escapes(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTMESH_WORKSPACE_ROOT", str(tmp_path))
    write_file("notes/example.txt", "hello")
    assert read_file("notes/example.txt") == "hello"
    assert list_dir("notes")[0]["name"] == "example.txt"
    with pytest.raises(ValueError):
        resolve_workspace_path("../outside.txt")
    with pytest.raises(ValueError):
        resolve_workspace_path(str(tmp_path / "absolute.txt"))


def test_python_exec_allows_calculator_code() -> None:
    result = run_python("import math\nprint(math.sqrt(16))")
    assert result["returncode"] == 0
    assert result["stdout"].strip() == "4.0"


def test_python_exec_blocks_disallowed_imports() -> None:
    with pytest.raises(ValueError):
        validate_python("import os\nprint(os.getcwd())")
    with pytest.raises(ValueError):
        validate_python("open('x', 'w')")


def test_memory_server_roundtrip(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTMESH_DATA_DIR", str(tmp_path))
    remembered = remember("LangGraph coordinates agent control flow.", ["langgraph", "agents"])
    results = recall("agent control", top_k=3)
    assert results
    assert results[0]["id"] == remembered["id"]
