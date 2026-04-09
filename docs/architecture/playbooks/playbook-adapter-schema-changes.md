# Playbook: Adapter Schema Changes

## Scope
Adapters and connectors that map upstream payloads.

## Explanation
Schema changes cause parsing failures or incorrect mapping. This playbook emphasizes tolerant parsing, version pinning, and adapter-side mapping updates.

## Triggers
- Parsing errors or missing required fields
- Contract test failures

## Triage
1. Capture failing payload samples.
2. Compare with expected schema and mapping.
3. Identify version or field changes upstream.
4. Check whether the change is additive within the current major or requires a major schema bump.

## Mitigation
- Add tolerant parsing for optional fields.
- Apply mapping hotfix in adapter layer.
- Pin upstream API version if available.
- Preserve canonical envelope compatibility by keeping additive changes within the same major version.
- Treat missing canonical `schema_version` as implicit `1.0` only during controlled migration windows.

## Prevention
- Add contract tests and schema validation.
- Monitor upstream change logs.
- Run `python scripts/ops/check_event_schema_contracts.py` before merge for canonical retail and connector envelope changes.

## Implementation Steps
1. Capture sample payloads in logs for failures.
2. Update mapping to handle optional/renamed fields.
3. Add or update `schema_version` contract tests for explicit-write and legacy-read coverage.
4. Bump the canonical major version before introducing breaking envelope changes.

## Code Examples

### Tolerant parsing with Pydantic
```python
from pydantic import BaseModel, ConfigDict

class ProductPayload(BaseModel):
	model_config = ConfigDict(extra="ignore")
	sku: str
	name: str
	price: float | None = None
```

### Adapter mapping fallback
```python
def map_product(payload: dict) -> dict:
	return {
		"sku": payload.get("sku") or payload.get("id"),
		"name": payload.get("name") or payload.get("title"),
		"price": payload.get("price") or payload.get("unit_price"),
	}
```

## Mermaid: Schema Change Handling
```mermaid
flowchart TD
	A[Schema error detected] --> B[Capture payload sample]
	B --> C[Update mapping + parser]
	C --> D[Add contract test]
	D --> E[Monitor upstream changes]
```

## Escalation
Notify integration owner with sample payload and impact.
