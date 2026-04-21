# AGC Edge-Path Bisection — 2026-04-21

| Field | Value |
|---|---|
| Date (UTC) | 2026-04-21 |
| Cluster | `holidaypeakhub405-dev-aks` (RG `holidaypeakhub405-dev-rg`) |
| AGC FQDN | `esbcc8bcfyazbbdg.fz03.alb.azure.com` → `4.252.129.79` |
| APIM FQDN | `holidaypeakhub405-dev-apim.azure-api.net` |
| Target service | `ecommerce-catalog-search` (ns `holiday-peak-agents`, port 8000) |
| ALB resource | `Microsoft.ServiceNetworking/trafficControllers/alb-d819fbfd` |
| Association subnet | `agc` (10.0.12.0/24), delegated to `Microsoft.ServiceNetworking/trafficControllers` |
| Subnet NSG | `agc-nsg` |

## Hop-by-hop evidence

| Hop | URL / check | Status | Elapsed | Notes |
|---|---|---|---|---|
| 1 | `GET http://127.0.0.1:8000/health` (pod-local) | 200 | 17 ms | App healthy |
| 1 | `GET http://127.0.0.1:8000/ready` (pod-local) | 200 | 354 ms | Foundry ready=true |
| 2 | `GET http://ecommerce-catalog-search-ecommerce-catalog-search.holiday-peak-agents.svc.cluster.local/health` | 200 | 6 ms | In-cluster service + kube-proxy OK |
| 3 | `Gateway holiday-peak-agc` + `HTTPRoute …-agc` status | OK | — | `Accepted=True`, `Programmed=True`, `ResolvedRefs=True`, `AttachedRoutes=2` |
| **4** | `GET http://esbcc8bcfyazbbdg.fz03.alb.azure.com/ecommerce-catalog-search/health` (in-cluster egress) | **—** | **12 003 ms** | **curl (28) Connection timed out, `time_connect=0` — TCP SYN never ACKed** |
| 4 | Same with explicit `Host: esbcc8bcfyazbbdg.fz03.alb.azure.com` header | — | 12 003 ms | Same TCP SYN timeout |
| 4 | `GET http://esbcc8bcfyazbbdg.fz03.alb.azure.com/api/health` (crud sanity) | — | 10 003 ms | Same — confirms the failure is NOT catalog-specific; the AGC edge is unreachable for any route |
| 5 | `GET https://esbcc8bcfyazbbdg.fz03.alb.azure.com/…` | — | 8 002 ms | TCP SYN timeout on 443 too |
| 5 | `Test-NetConnection 4.252.129.79:80` (local workstation) | FAIL | — | `TcpTestSucceeded=False`, `PingReply=DestinationHostUnreachable` |
| 5 | `Test-NetConnection 4.252.129.79:443` (local workstation) | FAIL | — | Same |
| 6 | APIM `/agents/ecommerce-catalog-search/*` | — | — | Not evaluated; upstream is blocked at hop 4 so APIM evidence is redundant |

**First failing hop: Hop 4 — AGC data-plane ingress.**
All control-plane signals (ALB provisioning, Gateway programming, HTTPRoute attachment) are green. The data-plane VIP `4.252.129.79` silently drops TCP SYN packets on both 80 and 443, from inside the AKS VNet and from the public Internet.

## Root cause

The user-defined NSG **`agc-nsg`** attached to subnet `agc` (10.0.12.0/24) has **zero custom inbound rules** (`securityRules: []`). The default Azure NSG rule set therefore governs inbound traffic, and rule **`DenyAllInBound`** at priority 65500 drops every TCP SYN destined for the AGC data-plane VIP. `AllowAzureLoadBalancerInBound` only matches the `AzureLoadBalancer` service tag (health probes), and `AllowVnetInBound` does not match Internet-sourced traffic — so requests from both Internet and in-cluster pods (whose pod IPs are source-translated to Internet when egressing to the public VIP) are dropped.

Repo source of the misconfiguration:

- `.infra/modules/shared-infrastructure/shared-infrastructure.bicep` → module `agcNsg` (lines ≈144–150) creates `agc-nsg` with `securityRules: []`.

Live Azure resource:

- `/subscriptions/150e82e8-25db-4f1a-8e04-a2f6a77d26c4/resourceGroups/holidaypeakhub405-dev-rg/providers/Microsoft.Network/networkSecurityGroups/agc-nsg`.

## Remediation — repo PR (primary)

Apply the following diff to [.infra/modules/shared-infrastructure/shared-infrastructure.bicep](.infra/modules/shared-infrastructure/shared-infrastructure.bicep#L144-L150):

```diff
 module agcNsg 'br/public:avm/res/network/network-security-group:0.5.3' = if (agcSupportEnabled) {
   name: 'nsg-agc'
   params: {
     name: 'agc-nsg'
     location: location
-    securityRules: []
+    securityRules: [
+      {
+        name: 'AllowGatewayManagerInbound'
+        properties: {
+          description: 'Required by Application Gateway for Containers for management traffic (ports 65200-65535).'
+          protocol: 'Tcp'
+          sourcePortRange: '*'
+          destinationPortRange: '65200-65535'
+          sourceAddressPrefix: 'GatewayManager'
+          destinationAddressPrefix: '*'
+          access: 'Allow'
+          priority: 100
+          direction: 'Inbound'
+        }
+      }
+      {
+        name: 'AllowInternetInboundHttp'
+        properties: {
+          description: 'AGC listener on port 80 must accept inbound traffic from the Internet.'
+          protocol: 'Tcp'
+          sourcePortRange: '*'
+          destinationPortRange: '80'
+          sourceAddressPrefix: 'Internet'
+          destinationAddressPrefix: '*'
+          access: 'Allow'
+          priority: 110
+          direction: 'Inbound'
+        }
+      }
+      {
+        name: 'AllowInternetInboundHttps'
+        properties: {
+          description: 'AGC listener on port 443 must accept inbound traffic from the Internet.'
+          protocol: 'Tcp'
+          sourcePortRange: '*'
+          destinationPortRange: '443'
+          sourceAddressPrefix: 'Internet'
+          destinationAddressPrefix: '*'
+          access: 'Allow'
+          priority: 120
+          direction: 'Inbound'
+        }
+      }
+    ]
     tags: tags
   }
 }
```

Rationale for each rule:

- **`AllowGatewayManagerInbound`** — AGC (Application Gateway for Containers) control plane pushes management traffic into the delegated subnet on ports 65200–65535 (service tag `GatewayManager`). Microsoft documents this as a requirement when the association subnet is covered by a user-defined NSG.
- **`AllowInternetInboundHttp` / `AllowInternetInboundHttps`** — the AGC data-plane VIP terminates listener traffic in the association subnet. Without explicit Internet→80/443 Allow rules, the default `DenyAllInBound` (65500) blocks client TCP SYNs. These rules preserve least-privilege (scoped to TCP 80 and 443) and keep SSH/RDP/etc. denied.

Propagation: after `azd provision` / `az deployment` re-applies the module, NSG updates are effective within seconds. The AGC data-plane should start accepting traffic on the next TCP SYN; no Gateway or HTTPRoute re-provisioning is required.

Deploy path (do **not** commit yet; user asked for working-tree only):

```powershell
# From repo root
azd provision                   # re-runs shared-infrastructure module
# OR targeted:
az deployment group create `
  --resource-group holidaypeakhub405-dev-rg `
  --template-file .infra/modules/shared-infrastructure/shared-infrastructure.bicep `
  --parameters @.infra/modules/shared-infrastructure/shared-infrastructure.parameters.json
```

## Remediation — live `az cli` runbook (fallback only, present for visibility — **NOT executed**)

If an operator needs to unblock before the Bicep PR merges, apply the same three rules directly to the NSG. These commands drift the live state from repo and MUST be followed by the Bicep PR to avoid a future `azd provision` reverting the change.

```bash
az network nsg rule create -g holidaypeakhub405-dev-rg --nsg-name agc-nsg \
  --name AllowGatewayManagerInbound --priority 100 --direction Inbound --access Allow \
  --protocol Tcp --source-address-prefixes GatewayManager --source-port-ranges '*' \
  --destination-address-prefixes '*' --destination-port-ranges 65200-65535

az network nsg rule create -g holidaypeakhub405-dev-rg --nsg-name agc-nsg \
  --name AllowInternetInboundHttp --priority 110 --direction Inbound --access Allow \
  --protocol Tcp --source-address-prefixes Internet --source-port-ranges '*' \
  --destination-address-prefixes '*' --destination-port-ranges 80

az network nsg rule create -g holidaypeakhub405-dev-rg --nsg-name agc-nsg \
  --name AllowInternetInboundHttps --priority 120 --direction Inbound --access Allow \
  --protocol Tcp --source-address-prefixes Internet --source-port-ranges '*' \
  --destination-address-prefixes '*' --destination-port-ranges 443
```

Validation after apply:

```bash
curl -sS -o /dev/null -w "code=%{http_code} time=%{time_total}\n" -m 10 \
  http://esbcc8bcfyazbbdg.fz03.alb.azure.com/ecommerce-catalog-search/health
# Expected: code=200 time=<1s
```

## What is NOT the cause (eliminated)

- **App / pod health** — pod-local `/health` and `/ready` return 200.
- **kube-proxy / Service endpoints** — in-cluster service DNS resolves and returns 200 in 6 ms.
- **Gateway API routing** — Gateway `Programmed=True`, HTTPRoute `Accepted=True, ResolvedRefs=True, Programmed=True`, `AttachedRoutes=2`. The route hostname matches the Gateway listener hostname.
- **ALB Controller** — two `alb-controller` pods running in `azure-alb-system`, reconciling without errors; leader election succeeded.
- **AGC resource state** — `trafficController`, `frontend` (`fe-617f852b` / fqdn `esbcc8bcfyazbbdg.fz03.alb.azure.com`), and `association` (`as-6c7155e7`, subnet `agc`) all report `provisioningState: Succeeded`.
- **DNS** — `esbcc8bcfyazbbdg.fz03.alb.azure.com` correctly resolves to `4.252.129.79`.
- **APIM** — not evaluated because the upstream (AGC) is unreachable; any APIM timeout is a downstream symptom of hop 4.

## Links

- Evidence JSON: [docs/ops/agc-bisection-2026-04-21.json](agc-bisection-2026-04-21.json)
- Guardrail script (PowerShell): [scripts/ops/agc-bisect.ps1](../../scripts/ops/agc-bisect.ps1)
- Guardrail script (bash): [scripts/ops/agc-bisect.sh](../../scripts/ops/agc-bisect.sh)
- MS docs — AGC NSG requirements: https://learn.microsoft.com/azure/application-gateway/for-containers/overview
