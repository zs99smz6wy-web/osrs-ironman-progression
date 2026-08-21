from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from evaluate_progression import DEFAULT_STATE, load_json, validate_account_state


def analyze_passive_status(account_state: dict[str, Any]) -> dict[str, Any]:
    """Report established loops and player observations without advancing any recurring system."""
    validate_account_state(account_state)
    observations = account_state["recurring_observations"]
    established_systems = sorted(
        system_id for system_id, established in account_state["passive_loops"].items() if established
    )

    return {
        "permanent_loop_establishment": {"established_systems": established_systems},
        "explicit_observations": observations,
        "established_systems_without_observation": [
            system_id for system_id in established_systems if system_id not in observations
        ],
        "elapsed_time_inferred": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Report player-observed recurring-system status without advancing timers or selecting a route."
    )
    parser.add_argument("state", nargs="?", default=DEFAULT_STATE, type=Path)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()

    result = analyze_passive_status(load_json(args.state))
    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    print(f"Established permanent loops: {', '.join(result['permanent_loop_establishment']['established_systems']) or 'none'}")
    print("Explicit observations:")
    for system_id, observation in result["explicit_observations"].items():
        ready_at = observation["ready_at"] if observation["ready_at"] is not None else "null"
        print(f"  - {system_id}: {observation['state']} (observed_at: {observation['observed_at']}; ready_at: {ready_at})")
    print(
        "Established systems without observation: "
        f"{', '.join(result['established_systems_without_observation']) or 'none'}"
    )
    print("Elapsed time inferred: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
