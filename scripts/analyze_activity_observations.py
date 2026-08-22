"""Report Sailing, Perilous Moons, and farming observations without simulating progression."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from evaluate_progression import DEFAULT_STATE, load_json, validate_account_state


MOON_EQUIPMENT_SET_IDS = {
    "blood_moon": (
        "blood_moon_helm",
        "blood_moon_chestplate",
        "blood_moon_tassets",
        "dual_macuahuitl",
    ),
    "blue_moon": (
        "blue_moon_helm",
        "blue_moon_chestplate",
        "blue_moon_tassets",
        "blue_moon_spear",
    ),
    "eclipse_moon": (
        "eclipse_moon_helm",
        "eclipse_moon_chestplate",
        "eclipse_moon_tassets",
        "eclipse_atlatl",
    ),
}


def analyze_activity_observations(account_state: dict[str, Any]) -> dict[str, Any]:
    """Return copied observations and explicit non-inference guarantees."""
    validate_account_state(account_state)

    unique_items = account_state["unique_item_observations"]
    moon_equipment = {
        set_id: {
            item_id: copy.deepcopy(unique_items[item_id])
            for item_id in item_ids
            if item_id in unique_items
        }
        for set_id, item_ids in MOON_EQUIPMENT_SET_IDS.items()
    }

    return {
        "sailing_observation": copy.deepcopy(account_state["sailing_observation"]),
        "perilous_moons_observation": copy.deepcopy(account_state["perilous_moons_observation"]),
        "moon_equipment_observations": moon_equipment,
        "farming_recurrence_observation": copy.deepcopy(account_state["farming_recurrence_observation"]),
        "clocks_advanced": False,
        "growth_inferred": False,
        "readiness_inferred": False,
        "loot_created": False,
        "reclaim_fee_calculated": False,
        "set_completion_inferred": False,
        "throughput_inferred": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Report player-observed Sailing, Perilous Moons, and farming state without "
            "advancing clocks, generating outcomes, or deriving readiness."
        )
    )
    parser.add_argument("state", nargs="?", default=DEFAULT_STATE, type=Path)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()

    result = analyze_activity_observations(load_json(args.state))
    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    print(f"Sailing observation: {'yes' if result['sailing_observation'] is not None else 'no'}")
    print(f"Perilous Moons observation: {'yes' if result['perilous_moons_observation'] is not None else 'no'}")
    moon_item_count = sum(len(items) for items in result["moon_equipment_observations"].values())
    print(f"Moon equipment observations: {moon_item_count}")
    print(
        "Farming recurrence observation: "
        f"{'yes' if result['farming_recurrence_observation'] is not None else 'no'}"
    )
    print("Clocks advanced: false")
    print("Readiness inferred: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
