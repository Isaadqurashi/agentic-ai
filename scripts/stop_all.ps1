$ErrorActionPreference = "SilentlyContinue"

Get-Job agentmesh-* | Stop-Job
Get-Job agentmesh-* | Remove-Job

function Stop-PortListener {
    param([int]$Port)
    $lines = netstat -ano | Select-String ":$Port\s+.*LISTENING"
    foreach ($line in $lines) {
        $parts = ($line.ToString().Trim() -split "\s+")
        $pidText = $parts[-1]
        if ($pidText -match "^\d+$") {
            Stop-Process -Id ([int]$pidText) -Force
        }
    }
}

foreach ($port in 9100, 9101, 9102, 9103, 8080) {
    Stop-PortListener -Port $port
}

Write-Host "Stopped Agentmesh jobs and listeners on ports 9100, 9101, 9102, 9103, and 8080."
