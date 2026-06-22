#!/usr/bin/env bash
set -euo pipefail

export DRY_RUN="${DRY_RUN:-true}"

wait_agent_card() {
  local port="$1"
  python - "$port" <<'PY'
import sys
import time
import urllib.request

port = sys.argv[1]
url = f"http://127.0.0.1:{port}/.well-known/agent-card.json"
for _ in range(30):
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            if response.status == 200:
                raise SystemExit(0)
    except Exception:
        time.sleep(1)
raise SystemExit(f"Agent card did not become healthy: {url}")
PY
}

python -m agentmesh.run_agent researcher &
wait_agent_card 9101
python -m agentmesh.run_agent coder &
wait_agent_card 9102
python -m agentmesh.run_agent fileops_memory &
wait_agent_card 9103
python -m agentmesh.run_agent orchestrator &
wait_agent_card 9100
python -m agentmesh.interfaces.web.server &

echo "Agentmesh is starting."
echo "Web UI: http://127.0.0.1:8080"
echo "CLI: python -m agentmesh.interfaces.cli"
wait
