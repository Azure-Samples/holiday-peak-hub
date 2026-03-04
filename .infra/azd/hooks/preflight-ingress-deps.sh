#!/usr/bin/env bash

set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <resource-group> <app-gateway-name>"
  exit 1
fi

RG="$1"
APP_GW_NAME="$2"

APP_GW_STATE=$(az network application-gateway show \
  --resource-group "$RG" \
  --name "$APP_GW_NAME" \
  --query "operationalState" -o tsv 2>/dev/null || true)

if [ "$APP_GW_STATE" != "Running" ]; then
  echo "App Gateway '$APP_GW_NAME' is not running (state='$APP_GW_STATE')."
  echo "Start it before deploying/syncing ingress-backed services."
  echo "Example: az network application-gateway start --resource-group $RG --name $APP_GW_NAME"
  exit 1
fi

AGIC_LABEL="app=ingress-appgw"
AGIC_NAMESPACE="kube-system"

if ! kubectl get pods -n "$AGIC_NAMESPACE" -l "$AGIC_LABEL" >/dev/null 2>&1; then
  echo "AGIC pod not found in namespace '$AGIC_NAMESPACE' with label '$AGIC_LABEL'."
  echo "Ingress-backed routing cannot be reconciled without AGIC."
  exit 1
fi

READY="$(kubectl get pods -n "$AGIC_NAMESPACE" -l "$AGIC_LABEL" -o jsonpath='{.items[0].status.containerStatuses[0].ready}' 2>/dev/null || true)"
RESTARTS="$(kubectl get pods -n "$AGIC_NAMESPACE" -l "$AGIC_LABEL" -o jsonpath='{.items[0].status.containerStatuses[0].restartCount}' 2>/dev/null || true)"

if [ "$READY" != "true" ]; then
  echo "AGIC is not ready (ready='$READY', restarts='$RESTARTS')."
  echo "Common cause: missing RBAC on App Gateway for AGIC managed identity."
  echo "Inspect with: kubectl logs -n $AGIC_NAMESPACE -l $AGIC_LABEL --tail=200"
  exit 1
fi

echo "Ingress dependency preflight passed."
