from __future__ import annotations

import sys
from pathlib import Path


def _prepend_path(path: Path) -> None:
    resolved = str(path.resolve())
    if resolved not in sys.path:
        sys.path.insert(0, resolved)


ROOT = Path(__file__).resolve().parent

_prepend_path(ROOT / "lib" / "src")

for app_src in (ROOT / "apps").glob("*/src"):
    _prepend_path(app_src)