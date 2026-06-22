# Agentmesh

Agentmesh is a custom multi-agent Python system. Each agent is a LangGraph graph, every tool is exposed through a custom MCP server, and agent-to-agent calls go over an A2A-style JSON-RPC network boundary with signed Agent Cards.

The only paid dependency in this project is the OpenAI API. Every tool is free and keyless by default.

The current default model for every agent is `gpt-4o-mini`, configured in `config/agents.yaml`.

## What It Does

Agentmesh runs several local agent servers:

- `orchestrator`: talks to the user, uses its own tools, and delegates work.
- `researcher`: web/weather research through MCP tools.
- `coder`: sandboxed file and Python execution tools.
- `fileops_memory`: local file operations and local memory tools.

The CLI and web UI talk to the Orchestrator over the same local A2A endpoint, so normal use exercises the real network path.

## Prerequisites

- Python 3.12 or newer
- PowerShell on Windows
- An OpenAI API key when `DRY_RUN=false`

Install dependencies:

```powershell
cd E:\Projects\ai-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
```

Create `.env`:

```powershell
Copy-Item .env.example .env
```

Edit `.env`:

```text
OPENAI_API_KEY=sk-proj-your-real-key
DRY_RUN=false
MAX_SESSION_USD=1.00
AGENTMESH_WORKSPACE_ROOT=.
AGENTMESH_DATA_DIR=.agentmesh_data
AGENTMESH_RECURSION_LIMIT=12
AGENTMESH_ENABLE_SQLITE_CHECKPOINTS=false
```

Do not commit `.env`. It is ignored by `.gitignore`.

## Dry Run

Dry run mode uses deterministic fake models. It requires no API key and spends nothing.

```powershell
cd E:\Projects\ai-agent
.\.venv\Scripts\Activate.ps1
.\scripts\stop_all.ps1
$env:DRY_RUN = "true"
Remove-Item Env:\OPENAI_API_KEY -ErrorAction SilentlyContinue
python -m pytest
.\scripts\start_all.ps1
```

In a second PowerShell window:

```powershell
cd E:\Projects\ai-agent
.\.venv\Scripts\Activate.ps1
$env:DRY_RUN = "true"
python -m agentmesh.interfaces.cli
```

Expected first prompt:

```text
you: hi
agentmesh [DRY_RUN:gpt-4o-mini] hi Available tools: ...
```

## Real OpenAI Mode

First check that your key in `.env` has the correct format:

```powershell
cd E:\Projects\ai-agent
.\.venv\Scripts\Activate.ps1
.\scripts\check_openai_key.ps1
```


Start all services:

```powershell
.\scripts\stop_all.ps1
$env:DRY_RUN = "false"
.\scripts\start_all.ps1
```

In a second PowerShell window:

```powershell
cd E:\Projects\ai-agent
.\.venv\Scripts\Activate.ps1
$env:DRY_RUN = "false"
python -m agentmesh.interfaces.cli
```

Try:

```text
hi
```

Then:

```text
Use the researcher agent to search for current Python packaging best practices and summarize them.
```

The CLI prints the running session cost after each message.

## Web UI

After `start_all.ps1` is running, open:

```text
http://127.0.0.1:8080
```

## Common Commands

Stop all local Agentmesh services:

```powershell
.\scripts\stop_all.ps1
```

Start all services:

```powershell
.\scripts\start_all.ps1
```

Run tests:

```powershell
$env:DRY_RUN = "true"
Remove-Item Env:\OPENAI_API_KEY -ErrorAction SilentlyContinue
python -m pytest
```

Check Agent Cards:

```powershell
Invoke-RestMethod http://127.0.0.1:9100/.well-known/agent-card.json
Invoke-RestMethod http://127.0.0.1:9101/.well-known/agent-card.json
```

View logs:

```powershell
Get-Content .\logs\orchestrator.log -Tail 100
Get-Content .\logs\researcher.log -Tail 100
```

## Useful Prompts

```text
What agents and tools do you have available?
```

```text
Use the researcher agent to compare LangGraph and CrewAI for building multi-agent systems. Give me a practical recommendation.
```

```text
Ask the coder agent to review this repository and identify the top five implementation risks.
```

```text
Remember this project goal: build a local multi-agent framework with MCP tools and A2A agent boundaries.
```

```text
Recall everything you know about this project goal and turn it into a short development checklist.
```

## Cost And Safety

- `MAX_SESSION_USD` controls the hard session budget.
- `DRY_RUN=true` disables OpenAI calls and uses fake deterministic models.
- `AGENTMESH_RECURSION_LIMIT` bounds LangGraph tool/LLM round trips.
- Specialist agents do not receive delegation tools; only the Orchestrator can delegate.
- Filesystem tools are sandboxed to `AGENTMESH_WORKSPACE_ROOT`.
- Python execution blocks dangerous imports and runs in a short subprocess.

## Troubleshooting

If the CLI prints `invalid_api_key`:

```powershell
.\scripts\check_openai_key.ps1
```

Fix `.env` so `OPENAI_API_KEY` starts with lowercase `sk-`. If the format is valid but OpenAI still rejects it, rotate the key in the OpenAI dashboard.

If a server returns `500`:

```powershell
Get-Content .\logs\orchestrator.log -Tail 120
```

If ports are stale:

```powershell
.\scripts\stop_all.ps1
.\scripts\start_all.ps1
```

If you change `.env`, restart services:

```powershell
.\scripts\stop_all.ps1
.\scripts\start_all.ps1
```

## Architecture

- MCP is vertical: agents talk to their own tools and data.
- A2A is horizontal: agents talk to other agents over local JSON-RPC.
- LangGraph is inside each agent: specialists use `create_agent`; the Orchestrator uses a visible `StateGraph` supervisor with a `ToolNode` and `tools_condition`.
- Tools are custom MCP servers under `agentmesh/mcp_servers/`.
- Agents are registered in `config/agents.yaml`.

## Adding A New Agent

For a standard persona-plus-tools agent, add one entry to `config/agents.yaml`:

```yaml
- id: trip_planner
  name: "Trip Planner Agent"
  description: "Plans trips using weather and web search tools."
  model: gpt-4o-mini
  system_prompt: "You are a meticulous trip-planning assistant..."
  mcp_servers: [weather_server, web_search_server]
  port: 9104
```

If a new tool is required, add an MCP server under `agentmesh/mcp_servers/` and register it in `config/mcp_servers.yaml`. Only use `custom_graph:` when the agent needs control flow beyond a simple persona and tool set.

## Model Notes

The project currently uses `gpt-4o-mini` for every agent. Model names and availability can change, so check the official model list before changing IDs:

```text
https://platform.openai.com/docs/models
```
