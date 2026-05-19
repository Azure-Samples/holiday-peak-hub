from pathlib import Path
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[2]
BASH_HOOK_PATH = ROOT / ".infra" / "azd" / "hooks" / "sync-apim-agents.sh"
POWERSHELL_HOOK_PATH = ROOT / ".infra" / "azd" / "hooks" / "sync-apim-agents.ps1"
HOOK_PATHS = (BASH_HOOK_PATH, POWERSHELL_HOOK_PATH)

RAW_CORS_VALUE = '<value>@(context.Request.Headers.GetValueOrDefault("Origin", "http://localhost:3000"))</value>'
ESCAPED_CORS_VALUE = '<value>@(context.Request.Headers.GetValueOrDefault(&quot;Origin&quot;, &quot;http://localhost:3000&quot;))</value>'


def _extract_bash_crud_policy(content: str) -> str:
    start_marker = 'cat > "$POLICY_XML_FILE" <<EOF\n'
    start = content.index(start_marker) + len(start_marker)
    end = content.index('\nEOF', start)
    return content[start:end]


def _extract_powershell_crud_policy(content: str) -> str:
    start_marker = '$crudPolicyXml = @"\n'
    start = content.index(start_marker) + len(start_marker)
    end = content.index('\n"@', start)
    return content[start:end]


def _extract_crud_policy(hook_path: Path) -> str:
    content = hook_path.read_text(encoding="utf-8")
    if hook_path.suffix == ".ps1":
        return _extract_powershell_crud_policy(content)
    return _extract_bash_crud_policy(content)


def test_crud_policy_cors_values_use_raw_quotes_in_xml_text() -> None:
    for hook_path in HOOK_PATHS:
        content = hook_path.read_text(encoding="utf-8")

        assert content.count(RAW_CORS_VALUE) == 2
        assert ESCAPED_CORS_VALUE not in content


def test_crud_policy_attribute_expressions_keep_xml_entities() -> None:
    for hook_path in HOOK_PATHS:
        content = hook_path.read_text(encoding="utf-8")

        assert 'condition="@(context.Request.OriginalUrl.Path.Equals(&quot;/api/health&quot;' in content
        assert 'condition="@(context.Request.OriginalUrl.Path.Equals(&quot;/api&quot;' in content
        assert 'template="@(string.Concat(&quot;/api&quot;, (string)context.Variables[&quot;crudBackendPath&quot;]))"' in content


def test_crud_policy_backend_has_single_forward_request_policy() -> None:
    for hook_path in HOOK_PATHS:
        policy_xml = _extract_crud_policy(hook_path)
        policy = ElementTree.fromstring(policy_xml)
        backend = policy.find("backend")

        assert backend is not None
        backend_policies = list(backend)
        assert len(backend_policies) == 1
        assert backend_policies[0].tag == "forward-request"
        assert backend_policies[0].attrib == {"timeout": "60"}