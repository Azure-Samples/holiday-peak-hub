"""Validate a generated Holiday Peak Hub ASB bundle."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LIB_SRC = REPO_ROOT / "lib" / "src"
if str(LIB_SRC) not in sys.path:
    sys.path.insert(0, str(LIB_SRC))

from holiday_peak_lib.evaluation import validate_bundle  # noqa: E402


def parse_args() -> argparse.Namespace:
    """Parse bundle validation command-line options."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-dir", required=True, help="Generated ASB bundle directory")
    return parser.parse_args()


def main() -> int:
    """Run bundle validation."""

    result = validate_bundle(Path(parse_args().bundle_dir).resolve())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passes"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
