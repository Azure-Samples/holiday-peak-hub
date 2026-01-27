"""Run a FastAPI app with lib reinstall on each restart.

This uses watchfiles to restart the process when source changes. Each restart
reinstalls the shared lib in editable mode to ensure the latest state is used.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run an app with lib reinstall on reload.")
    parser.add_argument("--app", required=True, help="Uvicorn app import path, e.g. pkg.main:app")
    parser.add_argument("--app-dir", required=True, help="Path to the app src directory")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--watch",
        action="append",
        default=[],
        help="Additional paths to watch; can be provided multiple times.",
    )
    return parser.parse_args()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _install_lib(repo_root: Path) -> None:
    lib_path = repo_root / "lib"
    try:
        import pip  # noqa: F401
    except Exception:  # pragma: no cover - fallback for venvs without pip
        subprocess.run([sys.executable, "-m", "ensurepip", "--upgrade"], check=True)
    subprocess.run([sys.executable, "-m", "pip", "install", "-e", str(lib_path)], check=True)


def _build_env(repo_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    lib_src = str(repo_root / "lib" / "src")
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{lib_src}{os.pathsep}{existing}" if existing else lib_src
    return env


def _run_app_process(
    *, repo_root: Path, app: str, app_dir: Path, host: str, port: int
) -> subprocess.Popen:
    _install_lib(repo_root)
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        app,
        "--host",
        host,
        "--port",
        str(port),
        "--app-dir",
        str(app_dir),
    ]
    return subprocess.Popen(cmd, env=_build_env(repo_root))


def main() -> int:
    args = _parse_args()
    repo_root = _repo_root()
    app_dir = Path(args.app_dir).resolve()
    watch_paths = [str(app_dir), str(repo_root / "lib" / "src"), *args.watch]

    try:
        from watchfiles import run_process
    except ImportError as exc:
        raise RuntimeError("watchfiles is required. Install it with: pip install watchfiles") from exc

    run_kwargs = {
        "repo_root": repo_root,
        "app": args.app,
        "app_dir": app_dir,
        "host": args.host,
        "port": args.port,
    }

    try:
        run_process(*watch_paths, target=_run_app_process, kwargs=run_kwargs)
    except PermissionError:
        os.environ.setdefault("WATCHFILES_FORCE_POLLING", "true")
        run_process(*watch_paths, target=_run_app_process, kwargs=run_kwargs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
