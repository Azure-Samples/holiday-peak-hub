from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "deploy-azd.yml"
VALIDATE_STEP_MARKER = "      - name: Validate AGC gateway class and direct CRUD health\n"
NEXT_SECTION_MARKER = "\n\n  sync-apim:\n"


def _validate_agc_readiness_block() -> str:
    content = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert content.count(VALIDATE_STEP_MARKER) == 1
    return content.split(VALIDATE_STEP_MARKER, 1)[1].split(NEXT_SECTION_MARKER, 1)[0]


def test_agc_readiness_validates_alb_and_traffic_controller_before_gateway_contract_and_direct_health() -> None:
    block = _validate_agc_readiness_block()

    assert 'SHARED_ALB_NAME="holiday-peak-agc"' in block
    assert 'SHARED_ALB_NAMESPACE="holiday-peak-crud"' in block
    assert 'kubectl get applicationloadbalancer "$SHARED_ALB_NAME" -n "$SHARED_ALB_NAMESPACE" -o json' in block
    assert 'ALB_ACCEPTED_STATUS' in block
    assert 'ALB_DEPLOYMENT_STATUS' in block
    assert 'az resource list -g "$AKS_NODE_RESOURCE_GROUP" --resource-type Microsoft.ServiceNetworking/trafficControllers --query' in block
    assert 'SHARED_GATEWAY_NAME="holiday-peak-agc"' in block
    assert 'SHARED_GATEWAY_NAMESPACE="holiday-peak-crud"' in block
    assert 'kubectl get gateway "$SHARED_GATEWAY_NAME" -n "$SHARED_GATEWAY_NAMESPACE" -o json' in block
    assert 'alb.networking.azure.io/alb-name' in block
    assert 'alb.networking.azure.io/alb-namespace' in block
    assert 'GATEWAY_ACCEPTED_STATUS' in block
    assert 'GATEWAY_ACCEPTED_MESSAGE' in block
    assert 'GATEWAY_PROGRAMMED_STATUS' in block
    assert 'GATEWAY_PROGRAMMED_MESSAGE' in block
    assert 'GATEWAY_STATUS_ADDRESS' in block
    assert 'validate_route_parent_status "crud-service"' in block
    assert 'probe_direct_agc_health "$(direct_health_path_for_service crud-service)" "direct-agc-crud-health"' in block

    alb_fetch = block.index('kubectl get applicationloadbalancer "$SHARED_ALB_NAME" -n "$SHARED_ALB_NAMESPACE" -o json')
    traffic_controller_guard = block.index('az resource list -g "$AKS_NODE_RESOURCE_GROUP" --resource-type Microsoft.ServiceNetworking/trafficControllers --query')
    gateway_fetch = block.index('kubectl get gateway "$SHARED_GATEWAY_NAME" -n "$SHARED_GATEWAY_NAMESPACE" -o json')
    route_check = block.index('validate_route_parent_status "crud-service"')
    direct_probe = block.index('probe_direct_agc_health "$(direct_health_path_for_service crud-service)" "direct-agc-crud-health"')

    assert alb_fetch < traffic_controller_guard < gateway_fetch < route_check < direct_probe


def test_agc_readiness_guard_clause_surfaces_actionable_agc_evidence() -> None:
    block = _validate_agc_readiness_block()

    assert 'Live shared ApplicationLoadBalancer evidence:' in block
    assert 'No healthy Azure Application Gateway for Containers trafficController with populated frontends and associations was found before Gateway validation.' in block
    assert 'Traffic controller evidence:' in block
    assert 'GatewayClass=\'%s\' alb.networking.azure.io/alb-name=\'%s\' alb.networking.azure.io/alb-namespace=\'%s\' Accepted=\'%s\' acceptedMessage=\'%s\' Programmed=\'%s\' programmedMessage=\'%s\' address=\'%s\'' in block
    assert 'Live shared Gateway evidence:' in block
    assert 'Route evidence:' in block
    assert 'is not fully deployed before Gateway validation.' in block
    assert 'is missing required AGC binding annotations before direct health validation.' in block
    assert 'is not Accepted before direct health validation.' in block
    assert 'is not Programmed before direct health validation.' in block
    assert 'has no status address before direct health validation.' in block
    assert 'has no parent status attached to shared Gateway' in block
    assert 'AGC readiness validation failed for ${AGC_FRONTEND_URL%/}${path}' in block


def test_agc_readiness_validates_changed_agent_routes_and_direct_health() -> None:
    block = _validate_agc_readiness_block()

    assert 'if [ -n "${CHANGED_AGENT_SERVICES:-}" ]; then' in block
    assert "IFS=',' read -r -a agent_services <<< \"${CHANGED_AGENT_SERVICES}\"" in block
    assert "printf '%s-%s-agc' \"$service_name\" \"$service_name\"" in block
    assert "printf '/%s/health' \"$service_name\"" in block
    assert 'validate_route_parent_status "$svc" "$(route_namespace_for_service "$svc")" "$(route_name_for_service "$svc")"' in block
    assert 'probe_direct_agc_health "$(direct_health_path_for_service "$svc")" "direct-agc-agent-health-${svc}"' in block