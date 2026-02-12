"""Typer CLI to deploy services via Bicep and maintain Dockerfiles."""
import subprocess
from pathlib import Path
from typing import Optional

import typer

app = typer.Typer(help="Provision Holiday Peak Hub services")

ROOT = Path(__file__).parent
APPS_DIR = ROOT.parent / "apps"
TEMPLATE_DIR = ROOT / "templates"
SHARED_INFRA_MAIN = ROOT / "modules" / "shared-infrastructure" / "shared-infrastructure-main.bicep"
STATIC_WEB_APP_MAIN = ROOT / "modules" / "static-web-app" / "static-web-app-main.bicep"
HELM_CHART_DIR = ROOT.parent / ".kubernetes" / "chart"

def load_template(template_name: str) -> str:
    path = TEMPLATE_DIR / template_name
    if not path.exists():
        raise typer.BadParameter(f"Template not found: {path}")
    return path.read_text(encoding="utf-8")


def deploy_file(
    file_path: Path,
    app_name: str,
    resource_group: str,
    location: str,
    app_image: str,
    subscription_id: Optional[str],
) -> None:
    typer.echo(
        f"Deploying {file_path.name} to {resource_group} in {location}"
    )
    cmd = [
        "az",
        "deployment",
        "sub",
        "create",
        "--location",
        location,
        "--template-file",
        str(file_path),
        "--parameters",
        f"location={location}",
        f"resourceGroupName={resource_group}",
        f"appName={app_name}",
        f"appImage={app_image}",
    ]
    if subscription_id:
        cmd.extend(["--subscription", subscription_id, "--parameters", f"subscriptionId={subscription_id}"])
    subprocess.run(cmd, check=False)


def deploy_subscription_template(
    template_path: Path,
    location: str,
    parameters: dict[str, str],
    subscription_id: Optional[str],
) -> None:
    if not template_path.exists():
        raise typer.BadParameter(f"Bicep file not found: {template_path}")
    cmd = [
        "az",
        "deployment",
        "sub",
        "create",
        "--location",
        location,
        "--template-file",
        str(template_path),
        "--parameters",
    ]
    for key, value in parameters.items():
        cmd.append(f"{key}={value}")
    if subscription_id:
        cmd.extend(["--subscription", subscription_id, "--parameters", f"subscriptionId={subscription_id}"])
    subprocess.run(cmd, check=False)


def deploy_helm_release(
    service: str,
    namespace: str,
    image_prefix: str,
    image_tag: str,
    enable_keda: bool,
) -> None:
    if not HELM_CHART_DIR.exists():
        raise typer.BadParameter(f"Helm chart not found: {HELM_CHART_DIR}")
    image_repo = f"{image_prefix}/{service}"
    cmd = [
        "helm",
        "upgrade",
        "--install",
        service,
        str(HELM_CHART_DIR),
        "--namespace",
        namespace,
        "--create-namespace",
        "--set",
        f"serviceName={service}",
        "--set",
        f"image.repository={image_repo}",
        "--set",
        f"image.tag={image_tag}",
        "--set",
        f"keda.enabled={str(enable_keda).lower()}",
    ]
    subprocess.run(cmd, check=False)


def default_resource_group(service: str) -> str:
    return f"{service}-rg"


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
def deploy(
    service: str,
    resource_group: Optional[str] = typer.Option(None, help="Name of the resource group to create/use"),
    location: str = typer.Option("eastus", help="Azure region"),
    app_image: Optional[str] = typer.Option(None, help="Container image to deploy to AKS"),
    subscription_id: Optional[str] = typer.Option(None, help="Azure subscription ID"),
) -> None:
    main_bicep = ROOT / "modules" / service / f"{service}-main.bicep"
    if not main_bicep.exists():
        typer.echo(f"No Bicep found for {service}; generating from template.")
        write_bicep_files(service)
    rg = resource_group or default_resource_group(service)
    image = app_image or f"ghcr.io/OWNER/{service}:latest"
    deploy_file(main_bicep, service, rg, location, image, subscription_id)


@app.command()
def deploy_shared(
    environment: str = typer.Option("dev", help="Environment name (dev, staging, prod, demo)"),
    location: str = typer.Option("eastus2", help="Azure region"),
    project_name: Optional[str] = typer.Option(None, help="Project name prefix"),
    resource_group: Optional[str] = typer.Option(None, help="Override resource group name"),
    subscription_id: Optional[str] = typer.Option(None, help="Azure subscription ID"),
) -> None:
    """Deploy shared infrastructure (Cosmos DB, AKS, Event Hubs, etc.)."""
    params: dict[str, str] = {
        "environment": environment,
        "location": location,
    }
    if project_name:
        params["projectName"] = project_name
    if resource_group:
        params["resourceGroupName"] = resource_group
    deploy_subscription_template(SHARED_INFRA_MAIN, location, params, subscription_id)


@app.command()
def deploy_static_web_app(
    environment: str = typer.Option("dev", help="Environment name (dev, staging, prod, demo)"),
    location: str = typer.Option("eastus2", help="Azure region (SWA supported)"),
    app_name: str = typer.Option("holidaypeakhub-ui", help="Static Web App name"),
    resource_group: Optional[str] = typer.Option(None, help="Resource group name"),
    repository_url: str = typer.Option(
        "https://github.com/Azure-Samples/holiday-peak-hub", help="GitHub repo URL"
    ),
    branch: str = typer.Option("main", help="Git branch"),
    subscription_id: Optional[str] = typer.Option(None, help="Azure subscription ID"),
) -> None:
    """Deploy Static Web App infrastructure."""
    params = {
        "environment": environment,
        "location": location,
        "appName": app_name,
        "repositoryUrl": repository_url,
        "branch": branch,
    }
    if resource_group:
        params["resourceGroupName"] = resource_group
    deploy_subscription_template(STATIC_WEB_APP_MAIN, location, params, subscription_id)


@app.command()
def deploy_full(
    environment: str = typer.Option("dev", help="Environment name (dev, staging, prod, demo)"),
    location: str = typer.Option("eastus2", help="Azure region"),
    project_name: Optional[str] = typer.Option(None, help="Project name prefix"),
    resource_group: Optional[str] = typer.Option(None, help="Override resource group name"),
    subscription_id: Optional[str] = typer.Option(None, help="Azure subscription ID"),
) -> None:
    """Deploy shared infrastructure and static web app."""
    deploy_shared(
        environment=environment,
        location=location,
        project_name=project_name,
        resource_group=resource_group,
        subscription_id=subscription_id,
    )
    deploy_static_web_app(
        environment=environment,
        location=location,
        resource_group=resource_group,
        subscription_id=subscription_id,
    )


@app.command()
def deploy_shared_services(
    namespace: str = typer.Option("holiday-peak", help="AKS namespace for services"),
    image_prefix: str = typer.Option(
        "ghcr.io/azure-samples",
        help="Image repository prefix (e.g., ghcr.io/azure-samples)",
    ),
    image_tag: str = typer.Option("latest", help="Image tag"),
    enable_keda: bool = typer.Option(False, help="Enable KEDA scaling in chart"),
) -> None:
    """Deploy all services to shared AKS via Helm chart (requires kubectl context)."""
    for app_path in APPS_DIR.iterdir():
        if not app_path.is_dir():
            continue
        deploy_helm_release(
            service=app_path.name,
            namespace=namespace,
            image_prefix=image_prefix,
            image_tag=image_tag,
            enable_keda=enable_keda,
        )


@app.command()
def deploy_shared_all(
    environment: str = typer.Option("dev", help="Environment name (dev, staging, prod, demo)"),
    location: str = typer.Option("eastus2", help="Azure region"),
    project_name: Optional[str] = typer.Option(None, help="Project name prefix"),
    resource_group: Optional[str] = typer.Option(None, help="Override resource group name"),
    subscription_id: Optional[str] = typer.Option(None, help="Azure subscription ID"),
    namespace: str = typer.Option("holiday-peak", help="AKS namespace for services"),
    image_prefix: str = typer.Option(
        "ghcr.io/azure-samples",
        help="Image repository prefix (e.g., ghcr.io/azure-samples)",
    ),
    image_tag: str = typer.Option("latest", help="Image tag"),
    enable_keda: bool = typer.Option(False, help="Enable KEDA scaling in chart"),
) -> None:
    """Deploy shared infra, static web app, then all services to shared AKS."""
    deploy_shared(
        environment=environment,
        location=location,
        project_name=project_name,
        resource_group=resource_group,
        subscription_id=subscription_id,
    )
    deploy_static_web_app(
        environment=environment,
        location=location,
        resource_group=resource_group,
        subscription_id=subscription_id,
    )
    deploy_shared_services(
        namespace=namespace,
        image_prefix=image_prefix,
        image_tag=image_tag,
        enable_keda=enable_keda,
    )


@app.command()
def deploy_all(
    resource_group_prefix: Optional[str] = typer.Option(None, help="Prefix for RG names; defaults to <service>-rg"),
    location: str = typer.Option("eastus", help="Azure region"),
    app_image: Optional[str] = typer.Option(None, help="Container image to deploy to AKS"),
    subscription_id: Optional[str] = typer.Option(None, help="Azure subscription ID"),
) -> None:
    for app_path in APPS_DIR.iterdir():
        if not app_path.is_dir():
            continue
        service = app_path.name
        main_bicep = ROOT / "modules" / service / f"{service}-main.bicep"
        if not main_bicep.exists():
            write_bicep_files(service)
        rg = resource_group_prefix or default_resource_group(service)
        image = app_image or f"ghcr.io/OWNER/{service}:latest"
        deploy_file(main_bicep, service, rg, location, image, subscription_id)


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
    docker_path = app_path / "src" / "Dockerfile"
    template = load_template("Dockerfile.template")
    content = template.format(app_name=app_name)
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
