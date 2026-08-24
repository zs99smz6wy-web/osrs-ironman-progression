from __future__ import annotations

from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTEXTS = ROOT / "strategy" / "combat-quest-readiness-contexts.json"

REQUIRED_CONTEXT_KEYS = {
    "id",
    "action_id",
    "fact_ids",
    "encounter_observation_key",
    "formal_eligibility_note",
    "tactical_options_note",
    "unobserved_note",
    "snapshot_note",
    "attempt_note",
    "timely_note",
}


def validate_context_document(context_document: dict[str, Any], action_ids: set[str]) -> list[dict[str, Any]]:
    if set(context_document) != {"schema_version", "scope", "contexts"}:
        raise ValueError("Combat quest readiness context document has invalid keys")
    if context_document["schema_version"] != 1 or not isinstance(context_document["scope"], str):
        raise ValueError("Combat quest readiness context document has invalid metadata")
    contexts = context_document["contexts"]
    if not isinstance(contexts, list):
        raise ValueError("Combat quest readiness contexts must be a list")

    ids: set[str] = set()
    action_contexts: set[str] = set()
    for context in contexts:
        if not isinstance(context, dict) or set(context) != REQUIRED_CONTEXT_KEYS:
            raise ValueError("Combat quest readiness context has invalid keys")
        for key in REQUIRED_CONTEXT_KEYS - {"fact_ids"}:
            if not isinstance(context[key], str) or not context[key].strip():
                raise ValueError(f"Combat quest readiness context {key} must be a non-empty string")
        if context["id"] in ids or context["action_id"] in action_contexts:
            raise ValueError("Combat quest readiness contexts must have unique IDs and action IDs")
        if context["action_id"] not in action_ids:
            raise ValueError("Combat quest readiness context references an unknown action")
        if not isinstance(context["fact_ids"], list) or not context["fact_ids"] or any(
            not isinstance(fact_id, str) or not fact_id.strip() for fact_id in context["fact_ids"]
        ):
            raise ValueError("Combat quest readiness context fact_ids must be non-empty strings")
        ids.add(context["id"])
        action_contexts.add(context["action_id"])
    return contexts


def analyze_combat_quest_readiness(
    context_document: dict[str, Any], actions_document: dict[str, Any], account_state: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    """Describe player-recorded practical context without changing action eligibility."""
    action_ids = {action["id"] for action in actions_document["actions"]}
    contexts = validate_context_document(context_document, action_ids)
    encounter_observations = account_state["encounter_observations"]
    readiness_snapshot = account_state["combat_readiness_observation"]
    results: dict[str, dict[str, Any]] = {}

    for context in contexts:
        observation = encounter_observations.get(context["encounter_observation_key"])
        successes = observation["successful_completions"] if observation is not None else None
        if successes is not None and successes > 0:
            status = "timely_after_observed_encounter"
            note = context["timely_note"]
        elif observation is not None:
            status = "needs_practical_readiness"
            note = context["attempt_note"]
        elif readiness_snapshot is not None:
            status = "needs_tactical_confirmation"
            note = context["snapshot_note"]
        else:
            status = "needs_practical_readiness"
            note = context["unobserved_note"]

        results[context["action_id"]] = {
            "context_id": context["id"],
            "status": status,
            "formal_eligibility_preserved": True,
            "fact_ids": context["fact_ids"],
            "tactical_options_note": context["tactical_options_note"],
            "note": note,
            "combat_snapshot_recorded": readiness_snapshot is not None,
            "encounter_attempt_recorded": observation is not None,
            "encounter_success_recorded": successes is not None and successes > 0,
            "combat_win_inferred": False,
            "supplies_inferred": False,
            "player_competence_inferred": False,
        }
    return results
