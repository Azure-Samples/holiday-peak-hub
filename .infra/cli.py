"""Typer CLI to scaffold Bicep modules and Dockerfiles for services."""
from pathlib import Path
from typing import Optional

import typer

app = typer.Typer(help="Scaffold infrastructure files for Holiday Peak Hub services")

ROOT = Path(__file__).parent
APPS_DIR = ROOT.parent / "apps"
TEMPLATE_DIR = ROOT / "templates"


def load_template(template_name: str) -> str:
    path = TEMPLATE_DIR / template_name
    if not path.exists():
        raise typer.BadParameter(f"Template not found: {path}")
    return path.read_text(encoding="utf-8")


def write_bicep_files(app_name: str) -> tuple[Path, Path]:
    module_dir = ROOT / "modules" / app_name
    module_dir.mkdir(parents=True, exist_ok=True)
    app_bicep = module_dir / f"{app_name}.bicep"
    main_bicep = module_dir / f"{app_name}-main.bicep"
    app_template = load_template("app.bicep.tpl")
    main_template = load_template("main.bicep.tpl")
    app_bicep.write_text(app_template.replace("{app_name}", app_name), encoding="utf-8")
    main_bicep.write_text(main_template.replace("{app_name}", app_name), encoding="utf-8")
    typer.echo(f"Wrote {app_bicep} and {main_bicep}")
    return app_bicep, main_bicep


@app.command()
def generate_bicep(
    service: Optional[str] = typer.Option(None, help="Service name under apps/ (omit to apply --all)"),
    apply_all: bool = typer.Option(False, help="Regenerate Bicep for all services"),
) -> None:
    if apply_all:
        for app_path in APPS_DIR.iterdir():
            if app_path.is_dir():
                write_bicep_files(app_path.name)
        return
    if not service:
        raise typer.BadParameter("Provide --service or --apply-all")
    app_path = APPS_DIR / service
    if not app_path.exists():
        raise typer.BadParameter(f"Unknown service path: {app_path}")
    write_bicep_files(service)


def write_dockerfile(app_path: Path) -> None:
    app_name = app_path.name
    module_name = app_name.replace("-", "_")
    docker_path = app_path / "src" / "Dockerfile"
    template = load_template("Dockerfile.template")
    content = template.format(app_name=app_name, module_name=module_name)
    docker_path.write_text(content, encoding="utf-8")
    typer.echo(f"Wrote Dockerfile for {app_name} to {docker_path}")


@app.command()
def generate_dockerfile(
    service: Optional[str] = typer.Option(None, help="Service name under apps/ (omit to apply --all)"),
    apply_all: bool = typer.Option(False, help="Regenerate Dockerfiles for all services"),
) -> None:
    if apply_all:
        for app_path in APPS_DIR.iterdir():
            if app_path.is_dir():
                write_dockerfile(app_path)
        return
    if not service:
        raise typer.BadParameter("Provide --service or --apply-all")
    app_path = APPS_DIR / service
    if not app_path.exists():
        raise typer.BadParameter(f"Unknown service path: {app_path}")
    write_dockerfile(app_path)


if __name__ == "__main__":
    app()
