#!/usr/bin/env bash
# deploy-truth-agents.sh — Deploy only the truth pipeline + search-enrichment agents.
#
# Usage:
#   .infra/azd/hooks/deploy-truth-agents.sh [environment]
#
# Defaults to the "truth-agents" AZD environment. Requires:
#   - azd CLI authenticated
#   - AKS credentials available
#   - Helm installed
#
# This script renders Helm manifests and runs azd deploy for each service
# in the truth + search-enrichment scope.

set -euo pipefail

ENVIRONMENT="${1:-truth-agents}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

TRUTH_AGENT_SERVICES=(
  "search-enrichment-agent"
  "truth-ingestion"
  "truth-enrichment"
  "truth-export"
  "truth-hitl"
)

echo "========================================="
echo "  Truth Agents Scoped Deployment"
echo "  Environment: $ENVIRONMENT"
echo "  Services:    ${TRUTH_AGENT_SERVICES[*]}"
echo "========================================="

# Load environment variables
eval "$(azd env get-values -e "$ENVIRONMENT" 2>/dev/null | sed 's/^/export /')" || true

for service in "${TRUTH_AGENT_SERVICES[@]}"; do
  echo ""
  echo "--- Deploying $service ---"

  # Render Helm manifests
  bash "$SCRIPT_DIR/render-helm.sh" "$service"

  # Deploy via azd
  azd deploy --service "$service" -e "$ENVIRONMENT" --no-prompt
done

echo ""
echo "========================================="
echo "  Truth Agents deployment complete."
echo "========================================="
