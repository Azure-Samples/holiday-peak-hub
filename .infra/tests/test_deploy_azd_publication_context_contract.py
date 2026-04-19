from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "deploy-azd.yml"
PUBLICATION_CONTEXT_MARKER = "      - name: Resolve publication context\n"
FINALIZE_MARKER = "      - name: Finalize AGC readiness target\n"


def _publication_context_blocks() -> list[str]:
    content = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert content.count(PUBLICATION_CONTEXT_MARKER) == 2
    return content.split(PUBLICATION_CONTEXT_MARKER)[1:3]


def _finalize_block() -> str:
    content = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert content.count(FINALIZE_MARKER) == 1
    return content.split(FINALIZE_MARKER, 1)[1].split(
        "\n\n      - name: Validate AGC gateway class and direct CRUD health\n",
        1,
    )[0]


def test_publication_context_recovers_agc_render_subnet_without_reusing_live_gateway_hostnames() -> None:
    for block in _publication_context_blocks():
        assert 'AGC_SUBNET_ID_VALUE="${{ needs.provision.outputs.AGC_SUBNET_ID }}"' in block
        assert 'get_first_alb_association() {' in block
        assert 'kubectl get applicationloadbalancer "$alb_name" -n "$alb_namespace" -o json 2>/dev/null \\' in block
        assert "Recovered AGC render subnet from the live shared ApplicationLoadBalancer association." in block
        assert 'alb.networking.azure.io/alb-name' in block
        assert 'alb.networking.azure.io/alb-namespace' in block
        assert "Recovered AGC render subnet from the ApplicationLoadBalancer referenced by the live shared Gateway." in block
        assert 'echo "AGC_SUBNET_ID=$AGC_SUBNET_ID_VALUE" >> "$GITHUB_ENV"' in block
        assert 'AGC_HOSTNAME_VALUE=' not in block
        assert 'echo "AGC_HOSTNAME=' not in block
        assert 'echo "AGC_FRONTEND_HOSTNAME=' not in block

        direct_alb_lookup = block.index(
            'AGC_SUBNET_ID_VALUE="$(get_first_alb_association "holiday-peak-agc" "holiday-peak-crud")"'
        )
        gateway_alb_lookup = block.index(
            'AGC_SUBNET_ID_VALUE="$(get_first_alb_association "$AGC_SHARED_ALB_NAME" "$AGC_SHARED_ALB_NAMESPACE")"'
        )
        export_subnet = block.index('echo "AGC_SUBNET_ID=$AGC_SUBNET_ID_VALUE" >> "$GITHUB_ENV"')

        assert direct_alb_lookup < gateway_alb_lookup < export_subnet


def test_finalize_agc_target_prefers_runtime_frontend_status_over_gateway_listener_spec() -> None:
    block = _finalize_block()

    assert 'AGC_FRONTEND_HOST_VALUE="${{ needs.provision.outputs.AGC_FRONTEND_HOSTNAME }}"' in block
    assert 'resolve_frontend_from_alb_resource_group() {' in block
    assert 'az network alb frontend list -g "$alb_resource_group" --alb-name "$alb_name" --query "[0].fqdn" -o tsv' in block
    assert "Resolved AGC frontend hostname from the live shared Gateway status address." in block
    assert ".status.addresses[]?" in block
    assert ".spec.listeners[]?" not in block