#Requires -Version 7
<#
.SYNOPSIS
  Probe or reconcile the Azure Key Vault secret and Azure Database for PostgreSQL Flexible Server admin password.

.DESCRIPTION
  Modes:
    probe                 (default, read-only)
    rotate-from-keyvault  (reset DB password FROM the current Key Vault secret)
    rotate-new            (generate new random, update BOTH Key Vault AND DB)

  Progress is emitted as JSON lines to stdout with fields step, mode, status, detail, ts.

.EXAMPLE
  ./reconcile-postgres-password.ps1 -ResourceGroup rg -ServerName srv -KeyVaultName kv -Mode probe -DryRun

.NOTES
  Exit codes: 0 success, 1 config/rotation failure, 2 invalid password, 3 unreachable.
#>
[CmdletBinding()]
param(
    [string] $SubscriptionId,
    [Parameter(Mandatory = $true)] [string] $ResourceGroup,
    [Parameter(Mandatory = $true)] [string] $ServerName,
    [string] $AdminUser = 'crud_admin',
    [Parameter(Mandatory = $true)] [string] $KeyVaultName,
    [string] $SecretName = 'postgres-admin-password',
    [ValidateSet('probe','rotate-from-keyvault','rotate-new')] [string] $Mode = 'probe',
    [switch] $DryRun
)

$ErrorActionPreference = 'Stop'
$script:ProbeStatus = 'unknown'
$script:SecretVersion = 'unknown'
$ServerFqdn = "$ServerName.postgres.database.azure.com"

function Write-JsonLog {
    param(
        [Parameter(Mandatory)] [string] $Step,
        [Parameter(Mandatory)] [string] $Status,
        [string] $Detail = ''
    )
    $payload = [ordered]@{
        step   = $Step
        mode   = $Mode
        status = $Status
        detail = ($Detail -replace '[\r\n]+',' ')
        ts     = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    }
    ($payload | ConvertTo-Json -Compress) | Write-Output
}

function Require-Binary {
    param([string] $Name, [string] $Hint)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        if ($DryRun) {
            Write-JsonLog -Step 'check-tools' -Status 'warning' -Detail "$Name not found on PATH (dry-run; continuing). Hint: $Hint"
            return
        }
        Write-JsonLog -Step 'check-tools' -Status 'error' -Detail "$Name not found on PATH. Hint: $Hint"
        exit 1
    }
}

function Write-ProbeReport {
    $report = [ordered]@{
        status         = $script:ProbeStatus
        server         = $ServerFqdn
        user           = $AdminUser
        secret_version = $script:SecretVersion
        checked_at     = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    }
    ($report | ConvertTo-Json -Compress) | Write-Output
}

Require-Binary -Name 'az'   -Hint 'install Azure CLI (https://aka.ms/InstallAzureCLI)'
Require-Binary -Name 'psql' -Hint 'install PostgreSQL client tools'
if ($Mode -eq 'rotate-new') {
    Require-Binary -Name 'openssl' -Hint 'install openssl (or provide an alternative in future revision)'
}
Write-JsonLog -Step 'check-tools' -Status 'ok' -Detail 'az, psql available'

if ($SubscriptionId) {
    if ($DryRun) {
        Write-JsonLog -Step 'set-subscription' -Status 'dry-run' -Detail "az account set --subscription $SubscriptionId"
    } else {
        & az account set --subscription $SubscriptionId | Out-Null
        Write-JsonLog -Step 'set-subscription' -Status 'ok' -Detail "subscription=$SubscriptionId"
    }
}

function Read-KeyVaultSecret {
    if ($DryRun) {
        Write-JsonLog -Step 'read-secret' -Status 'dry-run' -Detail "az keyvault secret show --vault-name $KeyVaultName --name $SecretName"
        $script:SecretVersion = 'dry-run'
        return ''
    }
    $raw = & az keyvault secret show --vault-name $KeyVaultName --name $SecretName --query '{value:value,id:id}' -o json 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-JsonLog -Step 'read-secret' -Status 'error' -Detail ([string]$raw)
        exit 1
    }
    $obj = $raw | ConvertFrom-Json
    $script:SecretVersion = ($obj.id -split '/')[-1]
    Write-JsonLog -Step 'read-secret' -Status 'ok' -Detail "vault=$KeyVaultName secret=$SecretName version=$($script:SecretVersion)"
    return $obj.value
}

function Invoke-Probe {
    param([string] $Password)
    if ($DryRun) {
        Write-JsonLog -Step 'probe-connection' -Status 'dry-run' -Detail "psql postgres://$AdminUser@$ServerFqdn:5432/postgres?sslmode=require"
        $script:ProbeStatus = 'dry-run'
        return 0
    }
    $env:PGPASSWORD = $Password
    try {
        $conn = "host=$ServerFqdn port=5432 dbname=postgres user=$AdminUser sslmode=require connect_timeout=10"
        $output = & psql $conn -v ON_ERROR_STOP=1 -At -c 'SELECT 1;' 2>&1
        $rc = $LASTEXITCODE
    } finally {
        Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
    }
    $flat = ($output | Out-String).Trim()
    if ($rc -eq 0) {
        $script:ProbeStatus = 'ok'
        Write-JsonLog -Step 'probe-connection' -Status 'ok' -Detail "server=$ServerFqdn user=$AdminUser"
        return 0
    }
    if ($flat -match '(?i)password authentication failed|invalidpassword') {
        $script:ProbeStatus = 'invalid_password'
        Write-JsonLog -Step 'probe-connection' -Status 'invalid_password' -Detail "server=$ServerFqdn user=$AdminUser"
        return 2
    }
    $script:ProbeStatus = 'unreachable'
    Write-JsonLog -Step 'probe-connection' -Status 'unreachable' -Detail "server=$ServerFqdn detail=$flat"
    return 3
}

function Set-ServerPassword {
    param([string] $Password)
    if ($DryRun) {
        Write-JsonLog -Step 'apply-password' -Status 'dry-run' -Detail "az postgres flexible-server update --name $ServerName --resource-group $ResourceGroup --admin-password ****"
        return $true
    }
    $out = & az postgres flexible-server update --resource-group $ResourceGroup --name $ServerName --admin-password $Password 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-JsonLog -Step 'apply-password' -Status 'error' -Detail ([string]$out)
        return $false
    }
    Write-JsonLog -Step 'apply-password' -Status 'ok' -Detail "server=$ServerName"
    return $true
}

function Set-KeyVaultSecret {
    param([string] $Value)
    if ($DryRun) {
        Write-JsonLog -Step 'set-secret' -Status 'dry-run' -Detail "az keyvault secret set --vault-name $KeyVaultName --name $SecretName --value ****"
        return $true
    }
    $out = & az keyvault secret set --vault-name $KeyVaultName --name $SecretName --value $Value --query 'id' -o tsv 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-JsonLog -Step 'set-secret' -Status 'error' -Detail ([string]$out)
        return $false
    }
    Write-JsonLog -Step 'set-secret' -Status 'ok' -Detail "id=$out"
    return $true
}

function New-RandomPassword {
    $bytes = New-Object byte[] 64
    [System.Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
    $alphabet = [char[]]'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789@#$%'
    $chars = for ($i = 0; $i -lt 40; $i++) { $alphabet[$bytes[$i] % $alphabet.Length] }
    -join $chars
}

switch ($Mode) {
    'probe' {
        $secret = Read-KeyVaultSecret
        if ($DryRun) {
            [void] (Invoke-Probe '')
            Write-ProbeReport
            exit 0
        }
        $rc = Invoke-Probe $secret
        Write-ProbeReport
        exit $rc
    }
    'rotate-from-keyvault' {
        $secret = Read-KeyVaultSecret
        if (-not $DryRun) {
            $rc = Invoke-Probe $secret
            if ($rc -eq 0) {
                $script:ProbeStatus = 'already_in_sync'
                Write-JsonLog -Step 'rotate-from-keyvault' -Status 'already_in_sync' -Detail 'no-op'
                Write-ProbeReport
                exit 0
            }
            if ($rc -eq 3) { Write-ProbeReport; exit 3 }
        }
        if (-not (Set-ServerPassword $secret)) { exit 1 }
        if ($DryRun) { $script:ProbeStatus = 'dry-run'; Write-ProbeReport; exit 0 }
        $rc = Invoke-Probe $secret
        Write-ProbeReport
        if ($rc -eq 0) { exit 0 }
        Write-JsonLog -Step 'rotate-from-keyvault' -Status 'error' -Detail "post-rotation probe rc=$rc"
        exit 1
    }
    'rotate-new' {
        $previous = Read-KeyVaultSecret
        if ($DryRun) {
            Write-JsonLog -Step 'generate-password' -Status 'dry-run' -Detail 'System.Security.Cryptography.RandomNumberGenerator'
            [void] (Set-ServerPassword 'dry-run')
            [void] (Set-KeyVaultSecret 'dry-run')
            $script:ProbeStatus = 'dry-run'
            Write-ProbeReport
            exit 0
        }
        $new = New-RandomPassword
        Write-JsonLog -Step 'generate-password' -Status 'ok' -Detail "length=$($new.Length)"
        if (-not (Set-ServerPassword $new)) { exit 1 }
        if (-not (Set-KeyVaultSecret $new)) {
            Write-JsonLog -Step 'rotate-new' -Status 'error' -Detail 'Key Vault update failed; rolling back DB password'
            if (-not (Set-ServerPassword $previous)) { Write-JsonLog -Step 'rollback' -Status 'error' -Detail 'rollback failed' }
            exit 1
        }
        $rc = Invoke-Probe $new
        Write-ProbeReport
        if ($rc -ne 0) {
            Write-JsonLog -Step 'rotate-new' -Status 'error' -Detail "post-rotation probe rc=$rc; rolling back"
            [void] (Set-ServerPassword $previous)
            [void] (Set-KeyVaultSecret $previous)
            exit 1
        }
        exit 0
    }
}
