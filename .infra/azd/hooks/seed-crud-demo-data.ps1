#!/usr/bin/env pwsh
param(
    [string]$Namespace = $(if ($env:K8S_NAMESPACE) { $env:K8S_NAMESPACE } else { 'holiday-peak' }),
    [string]$EnvironmentName = $(if ($env:AZURE_ENV_NAME) { $env:AZURE_ENV_NAME } else { 'dev' }),
    [int]$WaitTimeoutSeconds = 600,
    [bool]$EnableSeed = $(if ($env:DEMO_SEED_ENABLED) { $env:DEMO_SEED_ENABLED -eq 'true' } else { $true }),
    [bool]$FailOnError = $false
)

$ErrorActionPreference = 'Stop'

if (-not $EnableSeed) {
    Write-Host 'CRUD demo seed is disabled (DEMO_SEED_ENABLED=false). Skipping.'
    exit 0
}

if ($EnvironmentName -in @('prod', 'production')) {
    Write-Host "CRUD demo seed skipped for environment '$EnvironmentName'."
    exit 0
}

if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) {
    throw 'kubectl is required for CRUD demo seeding.'
}

$deploymentName = kubectl get deployment -n $Namespace -l app=crud-service -o jsonpath="{.items[0].metadata.name}" 2>$null
if (-not $deploymentName) {
  $message = "Could not resolve crud-service deployment in namespace '$Namespace'."
  if ($FailOnError) { throw $message }
  Write-Warning $message
  exit 0
}

$crudImage = kubectl get deployment $deploymentName -n $Namespace -o jsonpath="{.spec.template.spec.containers[0].image}" 2>$null
if (-not $crudImage) {
  $message = "Could not resolve CRUD image from deployment '$deploymentName'."
  if ($FailOnError) { throw $message }
  Write-Warning $message
  exit 0
}

function Get-EnvFromDeployment {
    param(
        [Parameter(Mandatory = $true)][string]$Deployment,
        [Parameter(Mandatory = $true)][string]$Namespace,
        [Parameter(Mandatory = $true)][string]$Name
    )

    $value = kubectl get deployment $Deployment -n $Namespace -o jsonpath="{.spec.template.spec.containers[0].env[?(@.name=='$Name')].value}" 2>$null
    return $value
}

$postgresHost = Get-EnvFromDeployment -Deployment $deploymentName -Namespace $Namespace -Name 'POSTGRES_HOST'
$postgresUser = Get-EnvFromDeployment -Deployment $deploymentName -Namespace $Namespace -Name 'POSTGRES_USER'
$postgresPassword = Get-EnvFromDeployment -Deployment $deploymentName -Namespace $Namespace -Name 'POSTGRES_PASSWORD'
$postgresAuthMode = Get-EnvFromDeployment -Deployment $deploymentName -Namespace $Namespace -Name 'POSTGRES_AUTH_MODE'
$postgresEntraScope = Get-EnvFromDeployment -Deployment $deploymentName -Namespace $Namespace -Name 'POSTGRES_ENTRA_SCOPE'
$postgresDatabase = Get-EnvFromDeployment -Deployment $deploymentName -Namespace $Namespace -Name 'POSTGRES_DATABASE'
$postgresPort = Get-EnvFromDeployment -Deployment $deploymentName -Namespace $Namespace -Name 'POSTGRES_PORT'
$postgresSsl = Get-EnvFromDeployment -Deployment $deploymentName -Namespace $Namespace -Name 'POSTGRES_SSL'

if (-not $postgresAuthMode) { $postgresAuthMode = 'password' }
if (-not $postgresDatabase) { $postgresDatabase = 'holiday_peak_crud' }
if (-not $postgresPort) { $postgresPort = '5432' }
if (-not $postgresSsl) { $postgresSsl = 'true' }
if (-not $postgresEntraScope) { $postgresEntraScope = 'https://ossrdbms-aad.database.windows.net/.default' }

if ($postgresAuthMode -eq 'entra') {
  if (-not $postgresHost -or -not $postgresUser) {
    $message = 'Missing PostgreSQL environment values from CRUD deployment (POSTGRES_HOST/POSTGRES_USER).'
    if ($FailOnError) { throw $message }
    Write-Warning $message
    exit 0
  }
} elseif (-not $postgresHost -or -not $postgresUser -or -not $postgresPassword) {
    $message = 'Missing PostgreSQL environment values from CRUD deployment (POSTGRES_HOST/POSTGRES_USER/POSTGRES_PASSWORD).'
    if ($FailOnError) { throw $message }
    Write-Warning $message
    exit 0
}

$crudPod = kubectl get pod -n $Namespace -l app=crud-service -o jsonpath="{.items[0].metadata.name}" 2>$null
if (-not $crudPod) {
  $message = "Could not resolve crud-service pod in namespace '$Namespace' for PostgreSQL connectivity check."
  if ($FailOnError) { throw $message }
  Write-Warning $message
  exit 0
}

kubectl exec -n $Namespace $crudPod -- sh -lc 'python - <<"PY"
import os, socket, sys
host = os.getenv("POSTGRES_HOST")
port = int(os.getenv("POSTGRES_PORT", "5432"))
s = socket.socket()
s.settimeout(5)
try:
  s.connect((host, port))
except Exception:
  sys.exit(1)
finally:
  s.close()
sys.exit(0)
PY' 2>$null

if ($LASTEXITCODE -ne 0) {
  $message = "Skipping CRUD demo seed because PostgreSQL is not reachable from pod '$crudPod' (host=$postgresHost port=$postgresPort)."
  if ($FailOnError) { throw $message }
  Write-Warning $message
  exit 0
}

$jobName = "crud-demo-seed-$(Get-Date -Format 'yyyyMMddHHmmss')"
$jobYaml = @"
apiVersion: batch/v1
kind: Job
metadata:
  name: $jobName
  namespace: $Namespace
spec:
  backoffLimit: 1
  ttlSecondsAfterFinished: 600
  template:
    spec:
      restartPolicy: Never
      tolerations:
        - key: workload
          operator: Equal
          value: crud
          effect: NoSchedule
        - key: workload
          operator: Equal
          value: agents
          effect: NoSchedule
      containers:
        - name: seed
          image: $crudImage
          imagePullPolicy: Always
          command: ["python", "-m", "crud_service.scripts.seed_demo_data"]
          env:
            - name: DEMO_ENVIRONMENT
              value: "$EnvironmentName"
            - name: POSTGRES_AUTH_MODE
              value: "$postgresAuthMode"
            - name: POSTGRES_ENTRA_SCOPE
              value: "$postgresEntraScope"
            - name: POSTGRES_HOST
              value: "$postgresHost"
            - name: POSTGRES_USER
              value: "$postgresUser"
            - name: POSTGRES_PASSWORD
              value: "$postgresPassword"
            - name: POSTGRES_DATABASE
              value: "$postgresDatabase"
            - name: POSTGRES_PORT
              value: "$postgresPort"
            - name: POSTGRES_SSL
              value: "$postgresSsl"
"@

$tempFile = Join-Path ([System.IO.Path]::GetTempPath()) "$jobName.yaml"
Set-Content -Path $tempFile -Value $jobYaml -Encoding UTF8
kubectl apply -f $tempFile *> $null
if ($LASTEXITCODE -ne 0) {
  $message = "Failed to create seed job '$jobName'."
  if ($FailOnError) { throw $message }
  Write-Warning $message
  exit 0
}

$timeout = "${WaitTimeoutSeconds}s"
kubectl wait --for=condition=complete "job/$jobName" -n $Namespace --timeout=$timeout *> $null
if ($LASTEXITCODE -ne 0) {
  kubectl get job $jobName -n $Namespace -o wide
  kubectl logs "job/$jobName" -n $Namespace *> $null
  $message = "CRUD demo seed job '$jobName' did not complete successfully within timeout (${WaitTimeoutSeconds}s)."
  if ($FailOnError) { throw $message }
  Write-Warning $message
  exit 0
}

kubectl logs "job/$jobName" -n $Namespace
if ($LASTEXITCODE -ne 0) {
  $message = "CRUD demo seed job '$jobName' completed but logs could not be retrieved."
  if ($FailOnError) { throw $message }
  Write-Warning $message
  exit 0
}

Write-Host "CRUD demo data seeding completed with job '$jobName'."