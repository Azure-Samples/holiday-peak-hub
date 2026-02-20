import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cli


def test_load_template_missing_raises(monkeypatch) -> None:
    monkeypatch.setattr(cli, "TEMPLATE_DIR", Path("/definitely-not-present"))

    try:
        cli.load_template("missing.tpl")
        assert False, "Expected an exception for missing template"
    except Exception as exc:  # pylint: disable=broad-exception-caught
        assert "Template not found" in str(exc)


def test_write_bicep_files_creates_outputs(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    monkeypatch.setattr(cli, "TEMPLATE_DIR", tmp_path / "templates")

    templates = tmp_path / "templates"
    templates.mkdir(parents=True, exist_ok=True)
    (templates / "app.bicep.tpl").write_text("module {app_name}", encoding="utf-8")
    (templates / "main.bicep.tpl").write_text("main {app_name}", encoding="utf-8")

    app_bicep, main_bicep = cli.write_bicep_files("sample-service")

    assert app_bicep.exists()
    assert main_bicep.exists()
    assert app_bicep.read_text(encoding="utf-8") == "module sample-service"
    assert main_bicep.read_text(encoding="utf-8") == "main sample-service"


def test_write_dockerfile_uses_template(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(cli, "TEMPLATE_DIR", tmp_path / "templates")

    templates = tmp_path / "templates"
    templates.mkdir(parents=True, exist_ok=True)
    (templates / "Dockerfile.template").write_text("FROM {app_name}", encoding="utf-8")

    app_path = tmp_path / "apps" / "sample-service"
    (app_path / "src").mkdir(parents=True, exist_ok=True)

    cli.write_dockerfile(app_path)

    dockerfile = app_path / "src" / "Dockerfile"
    assert dockerfile.exists()
    assert dockerfile.read_text(encoding="utf-8") == "FROM sample-service"
