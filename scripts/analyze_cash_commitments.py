from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from evaluate_progression import DEFAULT_STATE, load_json, validate_account_state


DEADLINE_ORDER = ("now", "next_goal", "near_term", "later")


def analyze_cash_commitments(account_state: dict[str, Any]) -> dict[str, Any]:
    """Describe declared cash pressure without selecting a money-making method."""
    validate_account_state(account_state)
    current_coins = account_state["resources"].get("coins", 0)
    deadline_rank = {deadline: index for index, deadline in enumerate(DEADLINE_ORDER)}
    ordered = sorted(
        enumerate(account_state["cash_commitments"]),
        key=lambda entry: (deadline_rank[entry[1]["deadline"]], entry[0]),
    )

    cumulative_required = 0
    commitments: list[dict[str, Any]] = []
    for _, commitment in ordered:
        cumulative_required += commitment["coins"]
        commitments.append(
            {
                **commitment,
                "cumulative_required": cumulative_required,
                "cumulative_shortfall": max(0, cumulative_required - current_coins),
            }
        )

    by_deadline = {
        deadline: sum(item["coins"] for item in account_state["cash_commitments"] if item["deadline"] == deadline)
        for deadline in DEADLINE_ORDER
    }
    return {
        "current_coins": current_coins,
        "committed_coins": cumulative_required,
        "total_shortfall": max(0, cumulative_required - current_coins),
        "coins_by_deadline": by_deadline,
        "ordered_commitments": commitments,
        "method_selected": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Report declared account cash commitments and cumulative shortfalls without selecting a route."
    )
    parser.add_argument("state", nargs="?", default=DEFAULT_STATE, type=Path)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()

    result = analyze_cash_commitments(load_json(args.state))
    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    print(f"Current coins: {result['current_coins']}")
    print(f"Declared commitments: {result['committed_coins']}")
    print(f"Total shortfall: {result['total_shortfall']}")
    for commitment in result["ordered_commitments"]:
        print(
            f"[{commitment['deadline']}] {commitment['purpose']}: {commitment['coins']} coins "
            f"(cumulative shortfall: {commitment['cumulative_shortfall']})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
