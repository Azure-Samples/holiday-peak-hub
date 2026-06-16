"""Export an ASB claim map for an existing bundle directory."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LIB_SRC = REPO_ROOT / "lib" / "src"
if str(LIB_SRC) not in sys.path:
    sys.path.insert(0, str(LIB_SRC))

from holiday_peak_lib.evaluation import export_claim_map  # noqa: E402


def parse_args() -> argparse.Namespace:
    """Parse claim-map export command-line options."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-dir", required=True, help="Generated ASB bundle directory")
    return parser.parse_args()


def main() -> int:
    """Run claim-map export."""

    bundle_dir = Path(parse_args().bundle_dir).resolve()
    export_claim_map(bundle_dir)
    print(f"Exported claim-map.yaml in {bundle_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
