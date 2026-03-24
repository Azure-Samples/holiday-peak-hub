param(
    [string]$Environment = "truth-agents"
)

<#
.SYNOPSIS
Deploy only the truth pipeline + search-enrichment agents.

.DESCRIPTION
Renders Helm manifests and runs azd deploy for each service in the truth +
search-enrichment scope. Defaults to the "truth-agents" AZD environment.

.PARAMETER Environment
AZD environment name. Defaults to "truth-agents".

.EXAMPLE
.\.infra\azd\hooks\deploy-truth-agents.ps1
.\.infra\azd\hooks\deploy-truth-agents.ps1 -Environment dev
#>

$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path "$scriptDir\..\..\..\"

$TruthAgentServices = @(
    "search-enrichment-agent"
    "truth-ingestion"
    "truth-enrichment"
    "truth-export"
    "truth-hitl"
)

Write-Host "========================================="
Write-Host "  Truth Agents Scoped Deployment"
Write-Host "  Environment: $Environment"
Write-Host "  Services:    $($TruthAgentServices -join ', ')"
Write-Host "========================================="

# Load environment variables
$envValues = azd env get-values -e $Environment 2>$null
if ($envValues) {
    foreach ($line in $envValues -split "`n") {
        $line = $line.Trim()
        if ($line -and $line -notlike '#*') {
            $eqIndex = $line.IndexOf('=')
            if ($eqIndex -gt 0) {
                $key = $line.Substring(0, $eqIndex)
                $value = $line.Substring($eqIndex + 1).Trim('"')
                [Environment]::SetEnvironmentVariable($key, $value)
            }
        }
    }
}

foreach ($service in $TruthAgentServices) {
    Write-Host ""
    Write-Host "--- Deploying $service ---"

    # Render Helm manifests
    & "$scriptDir\render-helm.ps1" -ServiceName $service

    # Deploy via azd
    azd deploy --service $service -e $Environment --no-prompt
}

Write-Host ""
Write-Host "========================================="
Write-Host "  Truth Agents deployment complete."
Write-Host "========================================="
