"""Validate research-only partial quest packages."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = ROOT / "research" / "partial-quest-packages"
MANIFEST = PACKAGE_DIR / "integration-manifest.json"
ACTIONS = ROOT / "data" / "progression" / "actions.json"
BOUNDARY_KEYS = {
    "route_selected",
    "partial_progress_is_quest_completion",
    "action_auto_applied",
    "items_or_rewards_inferred",
    "lamp_target_selected",
    "survival_inferred",
}


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def validate_package(package: Any, label: str) -> list[str]:
    errors: list[str] = []
    required = {
        "package_schema_version", "package_type", "quest_id", "quest_name", "status",
        "scope", "sources", "requirements", "checkpoints", "completion", "boundaries",
    }
    if not isinstance(package, dict) or set(package) != required:
        return [f"{label}: package fields are invalid"]
    if package["package_schema_version"] != 1 or package["package_type"] != "research-only-partial-quest":
        errors.append(f"{label}: package identity is invalid")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", package["quest_id"]):
        errors.append(f"{label}: quest_id is invalid")
    if package["status"] not in {"research", "integration-reviewed"}:
        errors.append(f"{label}: status is invalid")

    sources = package["sources"]
    source_ids: set[str] = set()
    if not isinstance(sources, list) or not sources:
        errors.append(f"{label}: sources must not be empty")
    else:
        for index, source in enumerate(sources):
            context = f"{label}.sources[{index}]"
            expected = {"id", "url", "used_for", "verified_at"}
            if not isinstance(source, dict) or set(source) != expected:
                errors.append(f"{context}: fields are invalid")
                continue
            source_id = source["id"]
            if source_id in source_ids:
                errors.append(f"{context}: duplicate source id")
            source_ids.add(source_id)
            parsed = urlparse(source["url"])
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                errors.append(f"{context}: URL is invalid")
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", source["verified_at"]):
                errors.append(f"{context}: verified_at is invalid")

    checkpoints = package["checkpoints"]
    if not isinstance(checkpoints, list) or len(checkpoints) < 2:
        errors.append(f"{label}: at least two checkpoints are required")
        checkpoints = []
    ids: set[str] = set()
    sequences: list[int] = []
    for index, checkpoint in enumerate(checkpoints):
        context = f"{label}.checkpoints[{index}]"
        expected = {"id", "sequence", "state", "location", "description", "item_changes", "hazards", "observation", "promotion", "source_ids"}
        if not isinstance(checkpoint, dict) or set(checkpoint) != expected:
            errors.append(f"{context}: fields are invalid")
            continue
        checkpoint_id = checkpoint["id"]
        if not isinstance(checkpoint_id, str) or not checkpoint_id.startswith("checkpoint:") or checkpoint_id in ids:
            errors.append(f"{context}: checkpoint id is invalid or duplicated")
        ids.add(checkpoint_id)
        if not isinstance(checkpoint["sequence"], int):
            errors.append(f"{context}: sequence must be an integer")
        else:
            sequences.append(checkpoint["sequence"])
        if checkpoint["state"] not in {"start", "in_progress", "completion", "post_completion"}:
            errors.append(f"{context}: state is invalid")
        observation = checkpoint["observation"]
        if not isinstance(observation, dict) or set(observation) != {"class", "instruction", "sufficient_by_itself", "runelite_boundary"}:
            errors.append(f"{context}: observation fields are invalid")
        elif observation["class"] not in {"quest_list", "inventory_or_equipment", "player_confirmation"}:
            errors.append(f"{context}: observation class is invalid")
        promotion = checkpoint["promotion"]
        if not isinstance(promotion, dict) or set(promotion) != {"status", "reason"}:
            errors.append(f"{context}: promotion fields are invalid")
        elif promotion["status"] == "normalized_completion" and checkpoint["state"] != "completion":
            errors.append(f"{context}: only completion checkpoints may be normalized completions")
        for source_id in checkpoint["source_ids"]:
            if source_id not in source_ids:
                errors.append(f"{context}: unknown source id {source_id}")
    if sequences != list(range(1, len(sequences) + 1)):
        errors.append(f"{label}: checkpoint sequences must be contiguous and ordered from 1")

    completion = package["completion"]
    if not isinstance(completion, dict) or set(completion) != {"normalized_action_id", "rewards", "unlocks", "post_completion_claims"}:
        errors.append(f"{label}: completion fields are invalid")
    elif completion["normalized_action_id"] is not None and not completion["normalized_action_id"].startswith("action:"):
        errors.append(f"{label}: normalized_action_id is invalid")

    boundaries = package["boundaries"]
    if not isinstance(boundaries, dict) or set(boundaries) != BOUNDARY_KEYS or any(value is not False for value in boundaries.values()):
        errors.append(f"{label}: all research boundaries must be present and false")
    return errors


def validate_manifest() -> tuple[dict[str, int], list[str]]:
    manifest = load_json(MANIFEST)
    action_ids = {action["id"] for action in load_json(ACTIONS)["actions"]}
    errors: list[str] = []
    if set(manifest) != {"manifest_schema_version", "package_type", "packages", "boundary"}:
        return {}, ["manifest: fields are invalid"]
    if manifest["manifest_schema_version"] != 1 or manifest["package_type"] != "research-only-partial-quest":
        errors.append("manifest: identity is invalid")
    package_names = manifest["packages"]
    if not isinstance(package_names, list) or len(package_names) != len(set(package_names)):
        errors.append("manifest: packages must be a unique array")
        package_names = []
    checkpoint_count = 0
    for name in package_names:
        path = PACKAGE_DIR / name
        if not path.is_file() or path.suffix != ".json":
            errors.append(f"manifest: missing JSON package {name}")
            continue
        package = load_json(path)
        errors.extend(validate_package(package, name))
        linked_action = package.get("completion", {}).get("normalized_action_id") if isinstance(package, dict) else None
        if linked_action is not None and linked_action not in action_ids:
            errors.append(f"{name}: unknown normalized completion action {linked_action}")
        checkpoint_count += len(package.get("checkpoints", [])) if isinstance(package, dict) else 0
    return {"packages": len(package_names), "checkpoints": checkpoint_count}, errors


def main() -> int:
    report, errors = validate_manifest()
    if errors:
        print("Partial quest package validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
