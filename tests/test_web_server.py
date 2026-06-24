from __future__ import annotations

import json

from agentmesh.interfaces.web.server import _sse_event


def test_sse_event_preserves_multiline_response_as_one_payload() -> None:
    response = "First line\nSecond line\nThird line"

    event = _sse_event(response)

    assert event.startswith("data: ")
    assert event.endswith("\n\n")
    assert json.loads(event.removeprefix("data: ").strip()) == response


def test_sse_error_event_has_named_event_and_encoded_payload() -> None:
    event = _sse_event("failure\nwith details", event="agent-error")
    lines = event.splitlines()

    assert lines[0] == "event: agent-error"
    assert json.loads(lines[1].removeprefix("data: ")) == "failure\nwith details"
