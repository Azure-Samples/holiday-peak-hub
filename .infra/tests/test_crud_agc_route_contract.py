from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
CRUD_HELMRELEASE_PATH = ROOT / ".kubernetes" / "releases" / "crud" / "crud-service.yaml"


def test_crud_agc_routes_include_public_api_and_probe_paths() -> None:
    helmrelease = yaml.safe_load(CRUD_HELMRELEASE_PATH.read_text(encoding="utf-8"))
    agc_paths = helmrelease["spec"]["values"]["agc"]["paths"]

    routes = {path["path"]: path["pathType"] for path in agc_paths}

    assert routes["/health"] == "PathPrefix"
    assert routes["/ready"] == "PathPrefix"
    assert routes["/api"] == "PathPrefix"