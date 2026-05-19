from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASH_HOOK_PATH = ROOT / ".infra" / "azd" / "hooks" / "sync-apim-agents.sh"
POWERSHELL_HOOK_PATH = ROOT / ".infra" / "azd" / "hooks" / "sync-apim-agents.ps1"
HOOK_PATHS = (BASH_HOOK_PATH, POWERSHELL_HOOK_PATH)

RAW_CORS_VALUE = '<value>@(context.Request.Headers.GetValueOrDefault("Origin", "http://localhost:3000"))</value>'
ESCAPED_CORS_VALUE = '<value>@(context.Request.Headers.GetValueOrDefault(&quot;Origin&quot;, &quot;http://localhost:3000&quot;))</value>'


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