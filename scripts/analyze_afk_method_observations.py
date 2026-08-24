"""Report recorded AFK-method state without inferring availability, safety, or results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evaluate_progression import DEFAULT_STATE, load_json, report_afk_method_observations


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Report explicit AFK-method observations without deriving progression state."
    )
    parser.add_argument("state", nargs="?", default=DEFAULT_STATE, type=Path)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()

    result = report_afk_method_observations(load_json(args.state))
    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    print(f"AFK method observations: {result['observation_count']}")
    print("Availability inferred: false")
    print("Safety inferred: false")
    print("Results inferred: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
