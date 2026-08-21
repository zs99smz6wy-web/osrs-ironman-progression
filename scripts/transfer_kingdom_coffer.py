from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from evaluate_progression import DEFAULT_STATE, load_json, validate_account_state


BASE_COFFER_CAP = 5_000_000
ROYAL_TROUBLE_COFFER_CAP = 7_500_000
ROYAL_TROUBLE_QUEST = "Royal Trouble"
VALID_DIRECTIONS = {"deposit", "withdraw"}


def _require_resource(resources: dict[str, Any], key: str) -> int:
    value = resources.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"Account state resources.{key} must be a non-negative integer")
    return value


def kingdom_coffer_cap(account_state: dict[str, Any]) -> int:
    """Return the verified coffer cap for the account's completed quest state."""
    return (
        ROYAL_TROUBLE_COFFER_CAP
        if ROYAL_TROUBLE_QUEST in account_state["quests_completed"]
        else BASE_COFFER_CAP
    )


def transfer_kingdom_coffer(
    account_state: dict[str, Any], direction: str, amount: int
) -> dict[str, Any]:
    """Return an in-memory state after one exact, player-confirmed coffer transfer.

    This does not write files or derive any Kingdom wages, approval, elapsed time, or
    collection output.
    """
    validate_account_state(account_state)
    if direction not in VALID_DIRECTIONS:
        raise ValueError(f"Kingdom coffer direction must be one of: {sorted(VALID_DIRECTIONS)}")
    if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
        raise ValueError("Kingdom coffer amount must be a positive integer")
    if not account_state["passive_loops"].get("kingdom", False):
        raise ValueError("Managing Miscellania must be unlocked before transferring coffer coins")

    resources = account_state["resources"]
    coins = _require_resource(resources, "coins")
    coffer_coins = _require_resource(resources, "kingdom_coffer_coins")
    coffer_cap = kingdom_coffer_cap(account_state)

    if coffer_coins > coffer_cap:
        raise ValueError(f"Kingdom coffer balance exceeds its {coffer_cap}-coin cap")
    if direction == "deposit":
        if amount > coins:
            raise ValueError("Kingdom coffer deposit would underflow resources.coins")
        if coffer_coins + amount > coffer_cap:
            raise ValueError(f"Kingdom coffer deposit would exceed its {coffer_cap}-coin cap")
    elif amount > coffer_coins:
        raise ValueError("Kingdom coffer withdrawal would underflow resources.kingdom_coffer_coins")

    next_state = copy.deepcopy(account_state)
    next_resources = next_state["resources"]
    if direction == "deposit":
        next_resources["coins"] -= amount
        next_resources["kingdom_coffer_coins"] += amount
    else:
        next_resources["coins"] += amount
        next_resources["kingdom_coffer_coins"] -= amount
    return next_state


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Simulate an exact Kingdom coffer deposit or withdrawal without writing the input state."
    )
    parser.add_argument("state", nargs="?", default=DEFAULT_STATE, type=Path)
    parser.add_argument("direction", choices=sorted(VALID_DIRECTIONS))
    parser.add_argument("amount", type=int)
    args = parser.parse_args()

    next_state = transfer_kingdom_coffer(load_json(args.state), args.direction, args.amount)
    print(json.dumps(next_state, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
