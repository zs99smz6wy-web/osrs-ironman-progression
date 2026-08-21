from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

from evaluate_progression import validate_account_state
from score_candidates import score_candidates
from apply_action import _validate_effect
from osrs_xp import SKILLS


ROOT = Path(__file__).resolve().parents[1]
FACTS_DIR = ROOT / "data" / "facts"
RESEARCH_DIR = ROOT / "research"
GRAPH_DIR = ROOT / "graph"
PROGRESSION_DIR = ROOT / "data" / "progression"
FIXTURES_DIR = ROOT / "tests" / "fixtures"

REQUIRED_FACT_KEYS = {"id", "name", "category", "status", "verified_at", "source_ids"}
VALID_CATEGORIES = {"quest", "transport", "activity", "minigame", "reward", "sailing", "afk", "bypass", "economy"}
VALID_STATUSES = {"verified", "needs_revalidation", "research_queue"}
REQUIRED_ACCOUNT_STATE_KEYS = {
    "skills",
    "skill_xp",
    "quests_completed",
    "completed_actions",
    "transport_flags",
    "milestones",
    "gear_thresholds",
    "items",
    "resources",
    "counters",
    "passive_loops",
    "attention_window",
    "notable_drops",
    "preferences",
}
VALID_PREDICATE_TYPES = {
    "skill_at_least",
    "quest_completed",
    "transport_flag",
    "milestone",
    "resource_at_least",
    "item_at_least",
    "counter_at_least",
    "passive_loop",
    "notable_drop",
    "gear_threshold",
}
VALID_OUTCOME_TYPES = {"quest_completed", "transport_flag", "milestone", "passive_loop"}
VALID_EDGE_TYPES = {"requires", "unlocks", "makes_obtainable", "alternative", "bypass", "produces", "improves"}
VALID_ACTION_KINDS = {"quest", "unlock", "activity", "passive_setup"}
REQUIRED_ACTION_KEYS = {"id", "name", "kind", "status", "fact_ids", "requirements", "preparation", "completion", "outcomes", "transition", "repeatable"}
def validate_condition(condition: dict, context: str, errors: list[str]) -> None:
    groups = [name for name in ("all", "any") if name in condition]
    if groups:
        if len(groups) != 1 or len(condition) != 1:
            errors.append(f"{context} condition must contain exactly one group")
            return
        children = condition[groups[0]]
        if not isinstance(children, list) or (groups[0] == "any" and not children):
            errors.append(f"{context} has invalid {groups[0]} group")
            return
        for index, child in enumerate(children):
            if not isinstance(child, dict):
                errors.append(f"{context}.{groups[0]}[{index}] must be an object")
            else:
                validate_condition(child, f"{context}.{groups[0]}[{index}]", errors)
        return

    predicate_type = condition.get("type")
    if set(condition) - {"type", "key", "value"}:
        errors.append(f"{context} has unexpected predicate keys")
    if predicate_type not in VALID_PREDICATE_TYPES or not isinstance(condition.get("key"), str):
        errors.append(f"{context} has invalid predicate")
    if predicate_type in {"skill_at_least", "resource_at_least", "item_at_least", "counter_at_least"}:
        if isinstance(condition.get("value"), bool) or not isinstance(condition.get("value"), int) or condition["value"] < 0:
            errors.append(f"{context} requires a non-negative integer value")
    if predicate_type == "skill_at_least" and condition.get("key") not in SKILLS:
        errors.append(f"{context} references unknown skill {condition.get('key')}")
    if predicate_type == "passive_loop" and "value" in condition and not isinstance(condition["value"], bool):
        errors.append(f"{context} passive_loop value must be boolean")


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    errors: list[str] = []
    sources = {source["id"] for source in load_json(RESEARCH_DIR / "sources.json")["sources"]}
    fact_ids: set[str] = set()
    fact_statuses: dict[str, str] = {}
    node_ids = {node["id"] for node in load_json(GRAPH_DIR / "nodes.json")["nodes"]}
    account_state = load_json(GRAPH_DIR / "account-state.example.json")

    try:
        validate_account_state(account_state)
    except ValueError as exc:
        errors.append(f"account-state.example.json: {exc}")

    for fixture_path in sorted(FIXTURES_DIR.glob("*.json")):
        try:
            validate_account_state(load_json(fixture_path))
        except ValueError as exc:
            errors.append(f"tests/fixtures/{fixture_path.name}: {exc}")

    missing_state_keys = REQUIRED_ACCOUNT_STATE_KEYS - account_state.keys()
    if missing_state_keys:
        errors.append(f"account-state.example.json missing {sorted(missing_state_keys)}")
    attention = account_state.get("attention_window", {})
    if not isinstance(attention.get("duration_minutes"), int) or attention.get("duration_minutes", 0) < 1:
        errors.append("account-state.example.json has invalid attention duration")
    if attention.get("mode") not in {"true_afk", "low_attention", "semi_afk", "active"}:
        errors.append("account-state.example.json has invalid attention mode")

    for path in sorted(FACTS_DIR.glob("*.json")):
        for record in load_json(path).get("records", []):
            missing = REQUIRED_FACT_KEYS - record.keys()
            if missing:
                errors.append(f"{path.name}:{record.get('id', '<missing id>')} missing {sorted(missing)}")
                continue
            if record["id"] in fact_ids:
                errors.append(f"duplicate fact id: {record['id']}")
            fact_ids.add(record["id"])
            fact_statuses[record["id"]] = record["status"]
            if record["category"] not in VALID_CATEGORIES:
                errors.append(f"{path.name}:{record['id']} has invalid category")
            if record["status"] not in VALID_STATUSES:
                errors.append(f"{path.name}:{record['id']} has invalid status")
            try:
                date.fromisoformat(record["verified_at"])
            except ValueError:
                errors.append(f"{path.name}:{record['id']} has invalid verified_at date")
            for source_id in record["source_ids"]:
                if source_id not in sources:
                    errors.append(f"{path.name}:{record['id']} references unknown source {source_id}")

    action_ids: set[str] = set()
    actions_document = load_json(PROGRESSION_DIR / "actions.json")
    if set(actions_document) != {"actions"} or not isinstance(actions_document.get("actions"), list):
        errors.append("actions.json must contain only an actions array")
    actions = actions_document.get("actions", [])
    for action in actions:
        action_id = action.get("id", "<missing id>")
        missing_action_keys = REQUIRED_ACTION_KEYS - action.keys()
        if missing_action_keys:
            errors.append(f"{action_id} missing {sorted(missing_action_keys)}")
        if set(action) - REQUIRED_ACTION_KEYS:
            errors.append(f"{action_id} has unexpected keys {sorted(set(action) - REQUIRED_ACTION_KEYS)}")
        if action_id in action_ids:
            errors.append(f"duplicate progression action id: {action_id}")
        action_ids.add(action_id)
        if action.get("status") != "verified":
            errors.append(f"{action_id} may only use verified status")
        if action.get("kind") not in VALID_ACTION_KINDS:
            errors.append(f"{action_id} has invalid kind")
        if not isinstance(action.get("name"), str) or not action.get("name"):
            errors.append(f"{action_id} has invalid name")
        linked_facts = action.get("fact_ids")
        if not isinstance(linked_facts, list) or not linked_facts or len(linked_facts) != len(set(linked_facts)):
            errors.append(f"{action_id} fact_ids must be a non-empty unique array")
            linked_facts = []
        for fact_id in linked_facts:
            if fact_id not in fact_ids:
                errors.append(f"{action_id} references unknown fact {fact_id}")
            elif fact_statuses[fact_id] != "verified":
                errors.append(f"{action_id} references non-verified fact {fact_id}")
        requirements = action.get("requirements")
        if not isinstance(requirements, dict):
            errors.append(f"{action_id} has invalid requirements")
        else:
            validate_condition(requirements, f"{action_id}.requirements", errors)
        preparation = action.get("preparation")
        if not isinstance(preparation, dict):
            errors.append(f"{action_id} has invalid preparation")
        else:
            validate_condition(preparation, f"{action_id}.preparation", errors)
        completion = action.get("completion")
        if not isinstance(completion, dict):
            errors.append(f"{action_id} has invalid completion")
        else:
            validate_condition(completion, f"{action_id}.completion", errors)
        if not isinstance(action.get("repeatable"), bool):
            errors.append(f"{action_id} has invalid repeatable flag")
        outcomes = action.get("outcomes")
        if not isinstance(outcomes, list):
            errors.append(f"{action_id} outcomes must be an array")
        else:
            for outcome in outcomes:
                if not isinstance(outcome, dict) or outcome.get("type") not in VALID_OUTCOME_TYPES or not isinstance(outcome.get("key"), str):
                    errors.append(f"{action_id} has invalid outcome {outcome}")
                    continue
                if set(outcome) - {"type", "key", "value"}:
                    errors.append(f"{action_id} outcome has unexpected keys")
                if outcome["type"] == "passive_loop" and "value" in outcome and not isinstance(outcome["value"], bool):
                    errors.append(f"{action_id} passive_loop outcome value must be boolean")

        transition = action.get("transition")
        if not isinstance(transition, dict) or set(transition) != {"effects", "options", "reported_effects"}:
            errors.append(f"{action_id} has invalid transition wrapper")
        else:
            option_ids: set[str] = set()
            effect_groups = [("transition", transition.get("effects", []))]
            for option in transition.get("options", []):
                option_id = option.get("id") if isinstance(option, dict) else None
                if not isinstance(option_id, str) or not option_id or option_id in option_ids:
                    errors.append(f"{action_id} has invalid or duplicate transition option")
                    continue
                option_ids.add(option_id)
                option_requires = option.get("requires")
                if not isinstance(option_requires, dict):
                    errors.append(f"{action_id}.{option_id} has invalid requirements")
                else:
                    validate_condition(option_requires, f"{action_id}.{option_id}.requires", errors)
                effect_groups.append((option_id, option.get("effects", [])))
                if not isinstance(option.get("reported_effects"), list):
                    errors.append(f"{action_id}.{option_id} reported_effects must be an array")
            for group_name, effects in effect_groups:
                if not isinstance(effects, list):
                    errors.append(f"{action_id}.{group_name} effects must be an array")
                    continue
                for effect in effects:
                    try:
                        _validate_effect(effect)
                    except ValueError as exc:
                        errors.append(f"{action_id}.{group_name}: {exc}")
                        continue
                    if effect.get("op") == "gain_xp" and effect.get("key") not in SKILLS:
                        errors.append(f"{action_id}.{group_name} XP effect references unknown skill {effect.get('key')}")
                    if effect.get("fact_id") not in linked_facts:
                        errors.append(f"{action_id}.{group_name} effect cites unlinked fact {effect.get('fact_id')}")
            reports = transition.get("reported_effects")
            if not isinstance(reports, list):
                errors.append(f"{action_id} reported_effects must be an array")
            else:
                for report in reports:
                    if not isinstance(report, dict) or not isinstance(report.get("type"), str):
                        errors.append(f"{action_id} has invalid reported effect")
                    elif report.get("type") == "xp_award":
                        errors.append(f"{action_id} fixed XP must use a gain_xp transition effect")
                    elif report.get("fact_id") not in linked_facts:
                        errors.append(f"{action_id} reported effect cites unlinked fact {report.get('fact_id')}")

    for completed_action in account_state.get("completed_actions", []):
        if completed_action not in action_ids:
            errors.append(f"account-state.example.json references unknown completed action {completed_action}")

    try:
        score_candidates(load_json(ROOT / "strategy" / "candidates.json"), actions_document, account_state)
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(f"strategy/candidates.json: {exc}")

    edge_signatures: set[tuple[str, str, str]] = set()
    for edge in load_json(GRAPH_DIR / "edges.json")["edges"]:
        if edge["from"] not in node_ids or edge["to"] not in node_ids:
            errors.append(f"graph edge has unknown endpoint: {edge}")
        if edge.get("type") not in VALID_EDGE_TYPES:
            errors.append(f"graph edge has invalid type: {edge}")
        signature = (edge["from"], edge["to"], edge["type"])
        if signature in edge_signatures:
            errors.append(f"duplicate graph edge: {signature}")
        edge_signatures.add(signature)

    if errors:
        print("Validation failed:")
        print("\n".join(f"- {error}" for error in errors))
        return 1

    print("Validation passed: facts, sources, normalized actions, account state, and graph endpoints are consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
