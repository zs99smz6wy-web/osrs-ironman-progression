"""Report Mastering Mixology timing context without simulating an activity session."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE = ROOT / "graph" / "account-state.example.json"
CONTEXT_PATH = ROOT / "strategy" / "mastering-mixology-contexts.json"
RESOURCE_KEYS = {
    "mox": "mixology_mox_resin",
    "aga": "mixology_aga_resin",
    "lye": "mixology_lye_resin",
}
CURRENCY_KEYS = {
    "currency:mixology:mox-resin": "mox",
    "currency:mixology:aga-resin": "aga",
    "currency:mixology:lye-resin": "lye",
}
POTION_REVIEW_EVENT = "potion-opportunity-cost-reviewed"
OBJECTIVE_PREFIXES = ("reward:", "xp", "enjoyment")


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def non_negative_integer(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def mixology_observation(state: dict[str, Any]) -> tuple[dict[str, Any] | None, bool]:
    observations = state.get("minigame_activity_observations")
    if not isinstance(observations, dict):
        return None, False
    observation = observations.get("mastering-mixology")
    return (copy.deepcopy(observation), isinstance(observation, dict))


def observed_resin(
    resources: dict[str, Any], observation: dict[str, Any] | None
) -> dict[str, int | None]:
    balances = {resin: non_negative_integer(resources.get(key)) for resin, key in RESOURCE_KEYS.items()}
    rows = observation.get("currency_balances", []) if observation else []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict) or row.get("currency_id") not in CURRENCY_KEYS:
            continue
        resin = CURRENCY_KEYS[row["currency_id"]]
        if balances[resin] is None:
            balances[resin] = non_negative_integer(row.get("amount"))
    return balances


def recipe_coverage(herblore_level: int | None, context: dict[str, Any]) -> dict[str, Any]:
    thresholds = context["activity"]["recipe_coverage_levels"]
    unlocked = [] if herblore_level is None else [level for level in thresholds if level <= herblore_level]
    full_level = context["activity"]["full_recipe_coverage_level"]
    return {
        "observed_herblore_level": herblore_level,
        "unlocked_recipe_levels": unlocked,
        "full_recipe_set_available": herblore_level is not None and herblore_level >= full_level,
        "full_recipe_set_level": full_level,
        "coverage_inferred_from_level_only": True,
        "orders_or_outputs_inferred": False,
    }


def reward_readiness(
    items: dict[str, Any],
    resin: dict[str, int | None],
    purchases: list[dict[str, Any]],
    targets: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    purchase_ids = {
        purchase.get("purchase_id")
        for purchase in purchases
        if isinstance(purchase, dict) and isinstance(purchase.get("purchase_id"), str)
    }
    report = []
    for target in targets:
        item_count = non_negative_integer(items.get(target["item_key"]))
        cost = target["cost"]
        values_known = all(resin[name] is not None for name in cost)
        report.append({
            "id": target["id"],
            "action_id": target["action_id"],
            "selected_objective": False,
            "item_count_observed": item_count,
            "confirmed_purchase_observed": target["id"] in purchase_ids,
            "fixed_cost": copy.deepcopy(cost),
            "resin_readiness": (
                "ready" if values_known and all(resin[name] >= cost[name] for name in cost)
                else "insufficient" if values_known
                else "unknown"
            ),
            "purchase_inferred": False,
        })
    return report


def analyze_mastering_mixology(account_state: dict[str, Any]) -> dict[str, Any]:
    """Return conservative Mixology context from supplied state and observations."""
    context = load_json(CONTEXT_PATH)
    skills = account_state.get("skills")
    quests = account_state.get("quests_completed")
    items = account_state.get("items")
    resources = account_state.get("resources")
    skills = skills if isinstance(skills, dict) else {}
    quests = quests if isinstance(quests, list) else []
    items = items if isinstance(items, dict) else {}
    resources = resources if isinstance(resources, dict) else {}

    herblore_level = non_negative_integer(skills.get("Herblore"))
    hard_access = context["activity"]["hard_access"]
    has_quest = hard_access["quest"] in quests
    has_level = herblore_level is not None and herblore_level >= hard_access["herblore_level"]
    missing_access = []
    if not has_level:
        missing_access.append(f"Herblore {hard_access['herblore_level']} unboosted")
    if not has_quest:
        missing_access.append(hard_access["quest"])

    observation, observation_present = mixology_observation(account_state)
    session = observation.get("session") if observation_present else None
    session = session if isinstance(session, dict) else {}
    local_supplies = observation.get("local_supplies") if observation_present else None
    local_supplies = copy.deepcopy(local_supplies) if isinstance(local_supplies, dict) else None
    input_signal_present = local_supplies is not None
    last_event = session.get("last_event")
    opportunity_review_observed = last_event == POTION_REVIEW_EVENT
    objective = session.get("mode")
    objective_present = isinstance(objective, str) and objective.startswith(OBJECTIVE_PREFIXES)
    purchases = observation.get("confirmed_purchases") if observation_present else []
    purchases = purchases if isinstance(purchases, list) else []
    resin = observed_resin(resources, observation)
    rewards = reward_readiness(items, resin, purchases, context["reward_targets"])

    selected_reward = objective.removeprefix("reward:") if isinstance(objective, str) and objective.startswith("reward:") else None
    for reward in rewards:
        reward["selected_objective"] = reward["id"] == selected_reward

    if missing_access:
        timing_status = "delay_hard_access"
    elif not objective_present:
        timing_status = "delay_missing_named_objective"
    elif not input_signal_present:
        timing_status = "delay_missing_observed_input_signal"
    elif not opportunity_review_observed:
        timing_status = "delay_potion_opportunity_cost_unobserved"
    else:
        timing_status = "enter_candidate"

    session_status = session.get("status") if isinstance(session.get("status"), str) else "unknown"
    if session_status in {"ended", "reset", "unavailable"}:
        stop_reentry_status = "stopped_or_reentry_candidate_observed"
    elif session_status == "active":
        stop_reentry_status = "active_session_observed"
    else:
        stop_reentry_status = "stop_or_reentry_not_observed"

    return {
        "hard_access": {
            "status": "eligible" if not missing_access else "blocked",
            "herblore_level_observed": herblore_level,
            "children_of_the_sun_completed_observed": has_quest,
            "missing": missing_access,
            "boosts_accepted": False,
        },
        "recipe_coverage": recipe_coverage(herblore_level, context),
        "observation_boundary": {
            "raw_mixology_observation_present": observation_present,
            "globally_registered_in_shared_evaluator": True,
            "local_supplies_observed": local_supplies,
            "input_signal_present": input_signal_present,
            "potion_opportunity_cost_review_observed": opportunity_review_observed,
            "named_objective_observed": objective if objective_present else None,
            "raw_session_status": session_status,
        },
        "resin_observations": {
            "balances": resin,
            "all_three_balances_observed": all(value is not None for value in resin.values()),
            "paste_or_resin_created": False,
        },
        "reward_readiness": rewards,
        "timing": {
            "status": timing_status,
            "route_timing_inferred": False,
            "enter_requires": copy.deepcopy(context["enter_delay_stop_reentry"]["enter_candidate"]),
            "delay_conditions": copy.deepcopy(context["enter_delay_stop_reentry"]["delay_conditions"]),
        },
        "stop_reentry": {
            "status": stop_reentry_status,
            "stop_conditions": copy.deepcopy(context["enter_delay_stop_reentry"]["stop_conditions"]),
            "reentry_conditions": copy.deepcopy(context["enter_delay_stop_reentry"]["reentry_conditions"]),
        },
        "herb_sack_boundary": context["herb_sack_boundary"],
        "inference_guarantees": {
            "herb_stock_inferred": False,
            "paste_conversion_inferred": False,
            "resin_inferred": False,
            "activity_output_inferred": False,
            "purchase_inferred": False,
            "xp_inferred": False,
            "route_timing_inferred": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Report Mastering Mixology access and observation context without simulating activity results."
    )
    parser.add_argument("state", nargs="?", default=DEFAULT_STATE, type=Path)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()

    result = analyze_mastering_mixology(load_json(args.state))
    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    print(f"Hard access: {result['hard_access']['status']}")
    print(f"Recipe coverage through 81: {result['recipe_coverage']['full_recipe_set_available']}")
    print(f"Timing: {result['timing']['status']}")
    print(f"Stop/re-entry: {result['stop_reentry']['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
