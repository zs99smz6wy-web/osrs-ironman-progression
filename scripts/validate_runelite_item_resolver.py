"""Validate the production RuneLite item-container resolver."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESOLVER_PATH = ROOT / "data" / "import" / "runelite-item-resolver.v1.json"
SOURCES_PATH = ROOT / "research" / "sources.json"
ACTIONS_PATH = ROOT / "data" / "progression" / "actions.json"
VALID_STATES = {"items", "resources"}
VALID_AGGREGATIONS = {"sum", "presence", "max"}


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def predicate_targets(value: Any) -> set[tuple[str, str]]:
    targets: set[tuple[str, str]] = set()
    if isinstance(value, dict):
        predicate_type = value.get("type")
        if predicate_type in {"item_at_least", "resource_at_least"}:
            targets.add(("items" if predicate_type == "item_at_least" else "resources", value["key"]))
        for nested in value.values():
            targets.update(predicate_targets(nested))
    elif isinstance(value, list):
        for nested in value:
            targets.update(predicate_targets(nested))
    return targets


def validate_resolver(
    resolver: dict[str, Any], *, source_ids: set[str], targets: set[tuple[str, str]]
) -> list[str]:
    errors: list[str] = []
    if resolver.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    mappings = resolver.get("mappings")
    unresolved = resolver.get("unresolved")
    if not isinstance(mappings, list) or not isinstance(unresolved, list):
        return [*errors, "mappings and unresolved must be arrays"]

    model_keys: set[tuple[str, str]] = set()
    item_owners: dict[int, tuple[str, str]] = {}
    for index, mapping in enumerate(mappings):
        context = f"mappings[{index}]"
        required = {
            "model_state", "model_key", "runelite_item_ids", "display_names", "aggregation",
            "source_ids", "checked_at", "notes",
        }
        if not isinstance(mapping, dict) or set(mapping) - (required | {"grouping_rationale", "item_id_values", "id_policy"}):
            errors.append(f"{context} has unexpected fields")
            continue
        if not required <= set(mapping):
            errors.append(f"{context} is missing {sorted(required - set(mapping))}")
            continue
        state, key = mapping["model_state"], mapping["model_key"]
        target = (state, key)
        if state not in VALID_STATES or not isinstance(key, str) or not key.strip():
            errors.append(f"{context} has invalid model target")
        elif target in model_keys:
            errors.append(f"duplicate model key {state}.{key}")
        else:
            model_keys.add(target)
            if target not in targets:
                errors.append(f"{context} target {state}.{key} is not a current item/resource predicate")
        aggregation = mapping["aggregation"]
        if aggregation not in VALID_AGGREGATIONS:
            errors.append(f"{context} has invalid aggregation {aggregation!r}")
        ids = mapping["runelite_item_ids"]
        if not isinstance(ids, list) or not ids or any(not isinstance(item_id, int) or isinstance(item_id, bool) or item_id <= 0 for item_id in ids):
            errors.append(f"{context} must have non-empty positive numeric runelite_item_ids")
            ids = []
        if len(ids) != len(set(ids)):
            errors.append(f"{context} repeats a RuneLite item ID")
        if not isinstance(mapping["display_names"], list) or len(mapping["display_names"]) != len(ids):
            errors.append(f"{context} display_names must align with runelite_item_ids")
        if not isinstance(mapping["source_ids"], list) or not mapping["source_ids"]:
            errors.append(f"{context} must cite at least one source")
        elif unknown := set(mapping["source_ids"]) - source_ids:
            errors.append(f"{context} references unknown sources {sorted(unknown)}")
        if not isinstance(mapping["checked_at"], str) or not mapping["checked_at"].strip():
            errors.append(f"{context} must have checked_at")
        if not isinstance(mapping["notes"], str) or not mapping["notes"].strip():
            errors.append(f"{context} must have notes")
        if len(ids) > 1 and (not isinstance(mapping.get("grouping_rationale"), str) or not mapping["grouping_rationale"].strip()):
            errors.append(f"{context} multi-ID mapping needs grouping_rationale")
        if aggregation == "max":
            values = mapping.get("item_id_values")
            if not isinstance(values, dict) or set(values) != {str(item_id) for item_id in ids}:
                errors.append(f"{context} max aggregation needs one item_id_values entry per ID")
            elif any(not isinstance(amount, int) or isinstance(amount, bool) or amount < 1 for amount in values.values()):
                errors.append(f"{context} item_id_values must be positive integers")
        elif "item_id_values" in mapping:
            errors.append(f"{context} item_id_values is valid only for max aggregation")
        for item_id in ids:
            owner = item_owners.get(item_id)
            if owner is not None and owner != target:
                policy = mapping.get("id_policy")
                if policy != "non_exclusive_group":
                    errors.append(f"{context} item ID {item_id} already maps to {owner[0]}.{owner[1]} without non_exclusive_group policy")
            else:
                item_owners[item_id] = target

    unresolved_keys: set[tuple[str, str]] = set()
    for index, entry in enumerate(unresolved):
        context = f"unresolved[{index}]"
        if not isinstance(entry, dict) or set(entry) != {"model_state", "model_key", "reason", "source_ids", "checked_at"}:
            errors.append(f"{context} has invalid fields")
            continue
        target = (entry["model_state"], entry["model_key"])
        if target in model_keys or target in unresolved_keys:
            errors.append(f"{context} duplicates a resolved or unresolved target")
        unresolved_keys.add(target)
        if entry["model_state"] not in VALID_STATES or not isinstance(entry["model_key"], str) or not entry["model_key"].strip():
            errors.append(f"{context} has invalid target")
        if not isinstance(entry["reason"], str) or not entry["reason"].strip():
            errors.append(f"{context} needs a reason")
        if not isinstance(entry["source_ids"], list) or not entry["source_ids"]:
            errors.append(f"{context} needs source_ids")
        elif unknown := set(entry["source_ids"]) - source_ids:
            errors.append(f"{context} references unknown sources {sorted(unknown)}")
    return errors


def main() -> int:
    resolver = load_json(RESOLVER_PATH)
    sources = {source["id"] for source in load_json(SOURCES_PATH)["sources"]}
    targets = predicate_targets(load_json(ACTIONS_PATH)["actions"])
    errors = validate_resolver(resolver, source_ids=sources, targets=targets)
    if errors:
        print("RuneLite item resolver validation failed:")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(f"RuneLite item resolver valid: {len(resolver['mappings'])} mappings, {len(resolver['unresolved'])} unresolved keys.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
