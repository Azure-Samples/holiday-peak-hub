#!/usr/bin/env sh
set -eu

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-${RESOURCE_GROUP:-}}"
AKS_CLUSTER_NAME="${AKS_CLUSTER_NAME:-}"
AGC_SUPPORT_ENABLED="${AGC_SUPPORT_ENABLED:-}"
AGC_CONTROLLER_IDENTITY_CLIENT_ID="${AGC_CONTROLLER_IDENTITY_CLIENT_ID:-}"
AGC_CONTROLLER_IDENTITY_PRINCIPAL_ID="${AGC_CONTROLLER_IDENTITY_PRINCIPAL_ID:-}"
AGC_SUBNET_ID="${AGC_SUBNET_ID:-}"
AKS_NODE_RESOURCE_GROUP="${AKS_NODE_RESOURCE_GROUP:-}"

resolve_env_value() {
  current_value="$1"
  shift

  if [ -n "$current_value" ]; then
    printf '%s' "$current_value"
    return 0
  fi

  if [ -z "${AZURE_ENV_NAME:-}" ]; then
    return 0
  fi

  env_file="$REPO_ROOT/.azure/$AZURE_ENV_NAME/.env"
  if [ ! -f "$env_file" ]; then
    return 0
  fi

  for key in "$@"; do
    value="$(grep -E "^${key}=" "$env_file" | head -n 1 | cut -d '=' -f2- | tr -d '"' || true)"
    if [ -n "$value" ]; then
      printf '%s' "$value"
      return 0
    fi
  done
}

require_role_assignment() {
  principal_id="$1"
  scope="$2"
  role_definition_id="$3"
  role_name="$4"

  existing_count="$(az role assignment list --assignee-object-id "$principal_id" --scope "$scope" --query "[?roleDefinitionId=='$role_definition_id'] | length(@)" -o tsv 2>/dev/null || true)"
  if [ -n "$existing_count" ] && [ "$existing_count" != "0" ]; then
    return 0
  fi

  echo "Required AGC controller role assignment '$role_name' ($role_definition_id) is missing at scope '$scope'. Re-run shared infrastructure provisioning before installing the ALB controller." >&2
  exit 1
}

AGC_SUPPORT_ENABLED="$(resolve_env_value "$AGC_SUPPORT_ENABLED" AGC_SUPPORT_ENABLED)"
if [ "${AGC_SUPPORT_ENABLED:-}" != "true" ]; then
  echo "AGC support is disabled for this environment. Skipping ALB controller installation."
  exit 0
fi

RESOURCE_GROUP="$(resolve_env_value "$RESOURCE_GROUP" AZURE_RESOURCE_GROUP resourceGroupName)"
AKS_CLUSTER_NAME="$(resolve_env_value "$AKS_CLUSTER_NAME" AKS_CLUSTER_NAME aksClusterName)"
AGC_CONTROLLER_IDENTITY_CLIENT_ID="$(resolve_env_value "$AGC_CONTROLLER_IDENTITY_CLIENT_ID" AGC_CONTROLLER_IDENTITY_CLIENT_ID)"
AGC_CONTROLLER_IDENTITY_PRINCIPAL_ID="$(resolve_env_value "$AGC_CONTROLLER_IDENTITY_PRINCIPAL_ID" AGC_CONTROLLER_IDENTITY_PRINCIPAL_ID)"
AGC_SUBNET_ID="$(resolve_env_value "$AGC_SUBNET_ID" AGC_SUBNET_ID)"
AKS_NODE_RESOURCE_GROUP="$(resolve_env_value "$AKS_NODE_RESOURCE_GROUP" AKS_NODE_RESOURCE_GROUP)"

if [ -z "$RESOURCE_GROUP" ]; then
  echo "Resource group could not be resolved. Set AZURE_RESOURCE_GROUP or run within an azd environment."
  exit 1
fi

if [ -z "$AKS_CLUSTER_NAME" ]; then
  echo "AKS cluster name could not be resolved. Set AKS_CLUSTER_NAME or run within an azd environment."
  exit 1
fi

if [ -z "$AGC_CONTROLLER_IDENTITY_CLIENT_ID" ]; then
  echo "AGC controller identity client ID could not be resolved. Provision shared infrastructure before running this hook."
  exit 1
fi

if [ -z "$AGC_CONTROLLER_IDENTITY_PRINCIPAL_ID" ]; then
  echo "AGC controller identity principal ID could not be resolved. Provision shared infrastructure before running this hook."
  exit 1
fi

if [ -z "$AGC_SUBNET_ID" ]; then
  echo "AGC subnet ID could not be resolved. Provision shared infrastructure before running this hook."
  exit 1
fi

if [ -z "$AKS_NODE_RESOURCE_GROUP" ]; then
  echo "AKS node resource group could not be resolved. Provision shared infrastructure before running this hook."
  exit 1
fi

for command_name in az kubectl helm; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Required command '$command_name' is not available on PATH."
    exit 1
  fi
done

echo "Installing AGC ALB controller support for cluster '$AKS_CLUSTER_NAME' in resource group '$RESOURCE_GROUP'."

SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
AKS_NODE_RESOURCE_GROUP_ID="/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$AKS_NODE_RESOURCE_GROUP"

require_role_assignment "$AGC_CONTROLLER_IDENTITY_PRINCIPAL_ID" "$AKS_NODE_RESOURCE_GROUP_ID" "acdd72a7-3385-48ef-bd42-f606fba81ae7" "Reader"
require_role_assignment "$AGC_CONTROLLER_IDENTITY_PRINCIPAL_ID" "$AKS_NODE_RESOURCE_GROUP_ID" "fbc52c3f-28ad-4303-a892-8a056630b8f1" "AppGw for Containers Configuration Manager"
require_role_assignment "$AGC_CONTROLLER_IDENTITY_PRINCIPAL_ID" "$AGC_SUBNET_ID" "4d97b98b-1d4f-4787-a291-c67834d212e7" "Network Contributor"

echo "Validated AGC controller RBAC prerequisites."

az aks get-credentials --resource-group "$RESOURCE_GROUP" --name "$AKS_CLUSTER_NAME" --overwrite-existing --only-show-errors >/dev/null

helm upgrade --install alb-controller oci://mcr.microsoft.com/application-lb/charts/alb-controller \
  --namespace azure-alb-system \
  --create-namespace \
  --version 1.9.13 \
  --set albController.namespace=azure-alb-system \
  --set "albController.podIdentity.clientID=$AGC_CONTROLLER_IDENTITY_CLIENT_ID" >/dev/null

kubectl rollout status deployment/alb-controller -n azure-alb-system --timeout=300s >/dev/null
kubectl get gatewayclass azure-alb-external -o name >/dev/null

echo "AGC ALB controller is ready."