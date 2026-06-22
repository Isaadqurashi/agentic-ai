$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$EnvPath = Join-Path $ProjectRoot ".env"
if (Test-Path $EnvPath) {
    Get-Content -LiteralPath $EnvPath | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
            $parts = $line.Split("=", 2)
            $key = $parts[0].Trim().TrimStart([char]0xFEFF)
            $value = $parts[1].Trim().Trim('"').Trim("'")
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
}

if (-not $env:DRY_RUN) {
    $env:DRY_RUN = "true"
}

$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    $Python = $VenvPython
} else {
    $Python = (Get-Command python).Source
}
$LogDir = Join-Path $ProjectRoot "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$agents = @("researcher", "coder", "fileops_memory", "orchestrator")
$ports = @{
    researcher = 9101
    coder = 9102
    fileops_memory = 9103
    orchestrator = 9100
}
$jobs = @()

function Stop-PortListener {
    param([int]$Port)
    $lines = netstat -ano | Select-String ":$Port\s+.*LISTENING"
    foreach ($line in $lines) {
        $parts = ($line.ToString().Trim() -split "\s+")
        $pidText = $parts[-1]
        if ($pidText -match "^\d+$") {
            Stop-Process -Id ([int]$pidText) -Force -ErrorAction SilentlyContinue
        }
    }
}

foreach ($port in @($ports.Values + 8080)) {
    Stop-PortListener -Port $port
}
Start-Sleep -Seconds 1

function Wait-AgentCard {
    param([int]$Port, [object]$Job, [string]$Log)
    $url = "http://127.0.0.1:$Port/.well-known/agent-card.json"
    for ($i = 0; $i -lt 30; $i++) {
        try {
            Invoke-RestMethod -Uri $url -TimeoutSec 2 | Out-Null
            return
        } catch {
            if ($Job.State -in @("Completed", "Failed", "Stopped")) {
                Write-Host "Agent job $($Job.Name) exited before becoming healthy. Last log lines:"
                if (Test-Path $Log) {
                    Get-Content -LiteralPath $Log -Tail 80
                }
                throw "Agent exited before becoming healthy: $url"
            }
            Start-Sleep -Seconds 1
        }
    }
    Write-Host "Timed out waiting for $url. Last log lines:"
    if (Test-Path $Log) {
        Get-Content -LiteralPath $Log -Tail 80
    }
    throw "Agent card did not become healthy: $url"
}

foreach ($agent in $agents) {
    $log = Join-Path $LogDir "$agent.log"
    $job = Start-Job -Name "agentmesh-$agent" -ScriptBlock {
        param($Python, $ProjectRoot, $Agent, $Log)
        Set-Location $ProjectRoot
        & $Python -m agentmesh.run_agent $Agent *> $Log
    } -ArgumentList $Python, $ProjectRoot, $agent, $log
    $jobs += $job
    Wait-AgentCard -Port $ports[$agent] -Job $job -Log $log
}

$jobs += Start-Job -Name "agentmesh-web" -ScriptBlock {
    param($Python, $ProjectRoot, $Log)
    Set-Location $ProjectRoot
    & $Python -m agentmesh.interfaces.web.server *> $Log
} -ArgumentList $Python, $ProjectRoot, (Join-Path $LogDir "web.log")

Write-Host "Agentmesh is starting."
Write-Host "Web UI: http://127.0.0.1:8080"
Write-Host "CLI: python -m agentmesh.interfaces.cli"
Write-Host "Logs: $LogDir"
Write-Host "Stop jobs with: Get-Job agentmesh-* | Stop-Job"
Write-Host "Job ids: $($jobs.Id -join ', ')"
