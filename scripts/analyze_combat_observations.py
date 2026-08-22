"""Report player-recorded combat observations without deriving readiness or a route."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from evaluate_progression import DEFAULT_STATE, load_json, validate_account_state


def analyze_combat_observations(account_state: dict[str, Any]) -> dict[str, Any]:
    """Expose observation windows and calculate rates only from explicitly measured fields."""
    validate_account_state(account_state)

    encounters: list[dict[str, Any]] = []
    for encounter_id, observation in sorted(account_state["encounter_observations"].items()):
        successes = observation["successful_completions"]
        elapsed_minutes = observation["elapsed_minutes"]
        rate = None
        if successes is not None and elapsed_minutes is not None and elapsed_minutes > 0:
            rate = successes * 60 / elapsed_minutes
        encounters.append(
            {
                "encounter_id": encounter_id,
                "observation": copy.deepcopy(observation),
                "measured_successes_per_hour": rate,
                "throughput_inferred": False,
            }
        )

    return {
        "combat_readiness_observation": copy.deepcopy(account_state["combat_readiness_observation"]),
        "encounters": encounters,
        "slayer_task_observation": copy.deepcopy(account_state["slayer_task"]),
        "unique_item_observations": copy.deepcopy(account_state["unique_item_observations"]),
        "readiness_inferred": False,
        "supply_use_inferred": False,
        "collection_log_inferred": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Report player-observed combat state without deriving gates, task assignments, or a route."
    )
    parser.add_argument("state", nargs="?", default=DEFAULT_STATE, type=Path)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()

    result = analyze_combat_observations(load_json(args.state))
    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    print(f"Combat readiness observed: {'yes' if result['combat_readiness_observation'] is not None else 'no'}")
    print(f"Encounter observations: {len(result['encounters'])}")
    for encounter in result["encounters"]:
        rate = encounter["measured_successes_per_hour"]
        rendered_rate = "not measured" if rate is None else f"{rate:g} successes/hour"
        print(f"  - {encounter['encounter_id']}: {rendered_rate}")
    print(f"Current Slayer task observed: {'yes' if result['slayer_task_observation'] is not None else 'no'}")
    print(f"Unique item observations: {len(result['unique_item_observations'])}")
    print("Readiness inferred: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
