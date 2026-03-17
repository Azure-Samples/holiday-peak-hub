param(
    [string]$BaseUrl,
    [string]$AzdEnvironment = $(if ($env:AZURE_ENV_NAME) { $env:AZURE_ENV_NAME } else { '' }),
    [string]$BearerToken = $env:CRUD_BEARER_TOKEN,
    [int]$TimeoutSec = 30,
    [switch]$UsePortForward = $false,
    [string]$ResourceGroup,
    [string]$AksName
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($BaseUrl) -and [string]::IsNullOrWhiteSpace($AzdEnvironment)) {
    throw "Provide -BaseUrl or set -AzdEnvironment/AZURE_ENV_NAME so the script can resolve APIM_GATEWAY_URL."
}

function Resolve-BaseUrl {
    param([string]$Provided, [string]$EnvName)

    if (-not [string]::IsNullOrWhiteSpace($Provided)) {
        return $Provided.TrimEnd('/')
    }

    $envLines = azd env get-values -e $EnvName 2>$null
    if (-not $envLines) {
        throw "BaseUrl not provided and could not load azd env '$EnvName'."
    }

    foreach ($line in $envLines) {
        if ($line -match '^APIM_GATEWAY_URL=') {
            $value = $line.Substring($line.IndexOf('=') + 1).Trim('"')
            if (-not [string]::IsNullOrWhiteSpace($value)) {
                return $value.TrimEnd('/')
            }
        }
    }

    throw "APIM_GATEWAY_URL not found in azd env '$EnvName'. Provide -BaseUrl explicitly."
}

function Get-AzdEnvMap {
    param([string]$EnvName)
    $map = @{}
    $envLines = azd env get-values -e $EnvName 2>$null
    if (-not $envLines) {
        return $map
    }
    foreach ($line in $envLines) {
        if ($line -match '^[A-Za-z_][A-Za-z0-9_]*=') {
            $idx = $line.IndexOf('=')
            $key = $line.Substring(0, $idx)
            $val = $line.Substring($idx + 1).Trim('"')
            $map[$key] = $val
        }
    }
    return $map
}

function Invoke-WriteCheck {
    param(
        [string]$Name,
        [string]$Path,
        [hashtable]$Body,
        [int[]]$ExpectedStatuses,
        [bool]$AuthRequired = $false,
        [hashtable]$ExtraHeaders = @{}
    )

    $headers = @{
        "Content-Type" = "application/json"
    }

    foreach ($k in $ExtraHeaders.Keys) {
        $headers[$k] = $ExtraHeaders[$k]
    }

    if ($AuthRequired) {
        if ([string]::IsNullOrWhiteSpace($script:Token)) {
            return [pscustomobject]@{
                Name = $Name
                Path = $Path
                StatusCode = "SKIP"
                Outcome = "SKIPPED"
                Detail = "Bearer token required"
            }
        }
        $headers["Authorization"] = "Bearer $script:Token"
    }

    $url = "$script:ResolvedBaseUrl$Path"
    try {
        $jsonBody = if ($null -eq $Body) { "{}" } else { $Body | ConvertTo-Json -Depth 10 }
        $response = Invoke-WebRequest -Uri $url -Method Post -Headers $headers -Body $jsonBody -TimeoutSec $script:TimeoutSec
        $status = [int]$response.StatusCode
        $content = $response.Content
    }
    catch {
        $status = -1
        $content = $_.Exception.Message

        if ($_.Exception.Response) {
            try {
                $status = [int]$_.Exception.Response.StatusCode.value__
            }
            catch {
                $status = -1
            }

            if ($_.ErrorDetails -and $_.ErrorDetails.Message) {
                $content = $_.ErrorDetails.Message
            }
        }
    }

    $ok = $ExpectedStatuses -contains $status
    $outcome = if ($ok) { "PASS" } else { "FAIL" }

    return [pscustomobject]@{
        Name = $Name
        Path = $Path
        StatusCode = $status
        Outcome = $outcome
        Detail = ($content | Out-String).Trim()
    }
}

$azdMap = Get-AzdEnvMap -EnvName $AzdEnvironment
$pfProcess = $null

if ($UsePortForward) {
    if ([string]::IsNullOrWhiteSpace($ResourceGroup)) {
        $ResourceGroup = $azdMap["AZURE_RESOURCE_GROUP"]
        if ([string]::IsNullOrWhiteSpace($ResourceGroup)) {
            $ResourceGroup = $azdMap["resourceGroupName"]
        }
    }

    if ([string]::IsNullOrWhiteSpace($AksName)) {
        $AksName = $azdMap["AKS_CLUSTER_NAME"]
        if ([string]::IsNullOrWhiteSpace($AksName)) {
            $AksName = $azdMap["AZURE_AKS_CLUSTER_NAME"]
        }
    }

    if ([string]::IsNullOrWhiteSpace($ResourceGroup) -or [string]::IsNullOrWhiteSpace($AksName)) {
        throw "UsePortForward requires AKS identifiers. Provide -ResourceGroup and -AksName or ensure azd env exposes AZURE_RESOURCE_GROUP/resourceGroupName and AKS_CLUSTER_NAME."
    }

    az aks get-credentials --resource-group $ResourceGroup --name $AksName --overwrite-existing | Out-Null
    $pfProcess = Start-Process -FilePath "kubectl" -ArgumentList @("port-forward", "svc/crud-service", "18080:8000", "-n", "holiday-peak") -PassThru -WindowStyle Hidden
    Start-Sleep -Seconds 4
    $script:ResolvedBaseUrl = "http://127.0.0.1:18080"
}
else {
    $script:ResolvedBaseUrl = Resolve-BaseUrl -Provided $BaseUrl -EnvName $AzdEnvironment
}

$script:Token = $BearerToken
$script:TimeoutSec = $TimeoutSec

Write-Host "CRUD POST write check"
Write-Host "Base URL: $script:ResolvedBaseUrl"
Write-Host "Auth token: $([string]::IsNullOrWhiteSpace($script:Token) ? 'not provided (auth routes will be skipped)' : 'provided')"

try {

# Resolve one product for dependent write endpoints.
$productId = "prd-electronics-001"
try {
    $productResp = Invoke-RestMethod -Uri "$script:ResolvedBaseUrl/api/products?limit=1" -Method Get -TimeoutSec $TimeoutSec
    if ($productResp -and $productResp[0] -and $productResp[0].id) {
        $productId = [string]$productResp[0].id
    }
}
catch {
    Write-Host "Could not read /api/products for dynamic seed context. Falling back to $productId"
}

$results = New-Object System.Collections.Generic.List[object]

# Non-auth POST endpoints.
$results.Add((Invoke-WriteCheck -Name "schemas-upsert" -Path "/api/schemas" -ExpectedStatuses @(200, 201) -Body @{
    category_id = "cat-write-check"
    category_name = "Write Check"
    version = "v1"
    fields = @(@{ name = "material"; type = "string"; required = $false; description = "Material" })
}))

$results.Add((Invoke-WriteCheck -Name "connector-replay-bulk" -Path "/webhooks/connectors/replay" -ExpectedStatuses @(200, 503) -Body @{ limit = 1 }))
$results.Add((Invoke-WriteCheck -Name "connector-replay-single" -Path "/webhooks/connectors/replay/dead-letter-write-check" -ExpectedStatuses @(200, 404, 503) -Body @{}))
$results.Add((Invoke-WriteCheck -Name "connector-webhook" -Path "/webhooks/connectors/shopify" -ExpectedStatuses @(202, 400, 503) -Body @{
    event_type = "product.updated"
    object_id = "prd-write-check"
    payload = @{ id = "prd-write-check"; title = "Write Check Product" }
}))
$results.Add((Invoke-WriteCheck -Name "stripe-webhook" -Path "/webhooks/stripe" -ExpectedStatuses @(200, 400, 503) -Body @{} -ExtraHeaders @{ "stripe-signature" = "write-check-signature" }))

# Auth-required POST endpoints.
$results.Add((Invoke-WriteCheck -Name "auth-logout" -Path "/api/auth/logout" -ExpectedStatuses @(200, 401) -Body @{} -AuthRequired $true))
$results.Add((Invoke-WriteCheck -Name "cart-add-item" -Path "/api/cart/items" -ExpectedStatuses @(200, 401, 404, 409, 422) -Body @{ product_id = $productId; quantity = 1 } -AuthRequired $true))
$results.Add((Invoke-WriteCheck -Name "checkout-validate" -Path "/api/checkout/validate" -ExpectedStatuses @(200, 400, 401, 422) -Body @{} -AuthRequired $true))

$orderResult = Invoke-WriteCheck -Name "orders-create" -Path "/api/orders" -ExpectedStatuses @(200, 400, 401, 422) -Body @{
    shipping_address_id = "addr-write-check"
    payment_method_id = "pm-write-check"
} -AuthRequired $true
$results.Add($orderResult)

$orderId = $null
if ($orderResult.Outcome -eq "PASS" -and $orderResult.StatusCode -eq 200 -and $orderResult.Detail) {
    try {
        $obj = $orderResult.Detail | ConvertFrom-Json
        $orderId = $obj.id
    }
    catch {}
}
if (-not $orderId) {
    $orderId = "order-write-check"
}

$results.Add((Invoke-WriteCheck -Name "reviews-create" -Path "/api/reviews" -ExpectedStatuses @(200, 401, 404, 422) -Body @{
    product_id = $productId
    rating = 5
    title = "Write check"
    comment = "Validated via CRUD POST write-check script"
} -AuthRequired $true))

$results.Add((Invoke-WriteCheck -Name "payments-intent" -Path "/api/payments/intent" -ExpectedStatuses @(200, 401, 402, 404, 422, 502, 503) -Body @{
    order_id = $orderId
    amount = 19.99
    currency = "usd"
} -AuthRequired $true))

$results.Add((Invoke-WriteCheck -Name "payments-process" -Path "/api/payments" -ExpectedStatuses @(200, 401, 402, 404, 422, 503) -Body @{
    order_id = $orderId
    payment_method_id = "pm_card_visa"
    amount = 19.99
} -AuthRequired $true))

$delegateResult = Invoke-WriteCheck -Name "acp-payments-delegate" -Path "/acp/payments/delegate" -ExpectedStatuses @(200, 401, 422) -Body @{
    payment_method_id = "pm_write_check"
    allowance = @{ amount = 100.00; currency = "USD" }
} -AuthRequired $true
$results.Add($delegateResult)

$paymentToken = $null
if ($delegateResult.Outcome -eq "PASS" -and $delegateResult.StatusCode -eq 200 -and $delegateResult.Detail) {
    try {
        $obj = $delegateResult.Detail | ConvertFrom-Json
        $paymentToken = $obj.token
    }
    catch {}
}
if (-not $paymentToken) {
    $paymentToken = "token-write-check"
}

$acpSessionResult = Invoke-WriteCheck -Name "acp-checkout-session-create" -Path "/acp/checkout/sessions" -ExpectedStatuses @(200, 400, 401, 422) -Body @{
    items = @(@{ sku = $productId; quantity = 1; unit_price = 19.99; currency = "USD" })
    currency = "USD"
} -AuthRequired $true
$results.Add($acpSessionResult)

$sessionId = $null
if ($acpSessionResult.Outcome -eq "PASS" -and $acpSessionResult.StatusCode -eq 200 -and $acpSessionResult.Detail) {
    try {
        $obj = $acpSessionResult.Detail | ConvertFrom-Json
        $sessionId = $obj.id
    }
    catch {}
}
if (-not $sessionId) {
    $sessionId = "session-write-check"
}

$results.Add((Invoke-WriteCheck -Name "acp-checkout-session-complete" -Path "/acp/checkout/sessions/$sessionId/complete" -ExpectedStatuses @(200, 400, 401, 404, 422) -Body @{ payment_token = $paymentToken } -AuthRequired $true))

$results | Format-Table -AutoSize Name, StatusCode, Outcome, Path

$failed = $results | Where-Object { $_.Outcome -eq "FAIL" }
if ($failed.Count -gt 0) {
    Write-Host "\nFailures:" -ForegroundColor Red
    foreach ($f in $failed) {
        Write-Host "- $($f.Name) [$($f.StatusCode)] $($f.Path)"
        if ($f.Detail) {
            Write-Host "  $($f.Detail.Substring(0, [Math]::Min($f.Detail.Length, 240)))"
        }
    }
    exit 1
}

Write-Host "\nAll POST endpoint checks passed or were intentionally skipped." -ForegroundColor Green
exit 0
}
finally {
    if ($pfProcess -and -not $pfProcess.HasExited) {
        Stop-Process -Id $pfProcess.Id -Force -ErrorAction SilentlyContinue
    }
}
