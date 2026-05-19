from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "deploy-azd.yml"
SMOKE_JOB_MARKER = "  smoke-apim:\n"
NEXT_JOB_MARKER = "\n\n  deploy-ui:\n"


def _smoke_apim_job() -> str:
    content = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert content.count(SMOKE_JOB_MARKER) == 1
    return content.split(SMOKE_JOB_MARKER, 1)[1].split(NEXT_JOB_MARKER, 1)[0]


def test_apim_cors_preflight_smoke_retries_header_validation() -> None:
    job = _smoke_apim_job()

    assert "smoke_cors_preflight() {" in job
    assert "for attempt in $(seq 1 20); do" in job
    assert "Access-Control-Request-Method: GET" in job
    assert 'local headers_file="/tmp/apim-cors-headers.txt"' in job
    assert 'local normalized_headers_file="/tmp/apim-cors-headers-normalized.txt"' in job
    assert ': > "$normalized_headers_file"' in job
    assert "tr -d '\\r' < \"$headers_file\" > \"$normalized_headers_file\"" in job
    assert "grep -Eiq '^Access-Control-Allow-Origin: http://localhost:3000$' \"$normalized_headers_file\"" in job
    assert "grep -Eiq '^Access-Control-Allow-Methods: .*GET' \"$normalized_headers_file\"" in job
    assert "grep -Eiq '^Access-Control-Allow-Origin: http://localhost:3000\\r?$' \"$headers_file\"" not in job
    assert "grep -Eiq '^Access-Control-Allow-Methods: .*GET' \"$headers_file\"" not in job
    assert "missing CORS headers" in job
    assert 'cat "$headers_file" 2>/dev/null || true' in job

    cors_function = job.index("smoke_cors_preflight() {")
    normalize_headers = job.index("tr -d '\\r' < \"$headers_file\" > \"$normalized_headers_file\"")
    origin_check = job.index("grep -Eiq '^Access-Control-Allow-Origin: http://localhost:3000$' \"$normalized_headers_file\"")
    cors_call = job.index('smoke_cors_preflight "${API_BASE}/api/products?limit=1" "crud-cors-preflight"')
    negative_probe = job.index('NEGATIVE_STATUS=$(curl -sS -o /tmp/apim-negative-response.json')

    assert cors_function < normalize_headers < origin_check < cors_call < negative_probe