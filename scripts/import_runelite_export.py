"""Import a bounded, local DZWNK Character Export snapshot into account state.

Phase 1 imports only permanent skill levels/XP and finished quests. It does not
infer unlocks, touch item containers, or convert diary data into progression.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from evaluate_progression import DEFAULT_STATE, load_json, validate_account_state
from osrs_xp import SKILLS, level_from_xp


ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_PLUGIN_VERSION = "0.6.0"
REQUIRED_DATASETS = ("character", "quests")
OPTIONAL_DATASETS = (
    "diaries", "bank", "seed_vault", "inventory", "equipment",
    "combat_achievements", "collection_log",
)
QUEST_STATES = {"NOT_STARTED", "IN_PROGRESS", "FINISHED"}
FOLDER_UNSAFE_CHARACTERS = re.compile(r"[^A-Za-z0-9_\- ]")


class ImportError(ValueError):
    """Raised when an export is incomplete, inconsistent, or unsupported."""


def sanitize_account_name(account_name: str) -> str:
    """Match Character Export v0.6.0's account-directory sanitization."""
    if not isinstance(account_name, str) or not account_name.strip():
        raise ImportError("account name must be a non-empty string")
    return FOLDER_UNSAFE_CHARACTERS.sub("_", account_name)


def resolve_account_directory(
    *,
    account_directory: Path | None = None,
    export_root: Path | None = None,
    account_name: str | None = None,
) -> Path:
    """Resolve exactly one export directory without guessing at account data."""
    if account_directory is not None:
        if export_root is not None or account_name is not None:
            raise ImportError("--account-directory cannot be combined with --export-root or --account-name")
        if not account_directory.is_dir():
            raise ImportError(f"account directory does not exist: {account_directory}")
        return account_directory.resolve()

    if export_root is None or account_name is None:
        raise ImportError("provide --account-directory or both --export-root and --account-name")
    if not export_root.is_dir():
        raise ImportError(f"export root does not exist: {export_root}")

    expected = sanitize_account_name(account_name).casefold()
    matches = [path for path in export_root.iterdir() if path.is_dir() and path.name.casefold() == expected]
    if not matches:
        raise ImportError(f"no Character Export folder matches account name {account_name!r}")
    if len(matches) != 1:
        raise ImportError(f"ambiguous Character Export folders match account name {account_name!r}")
    return matches[0].resolve()


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _require_object(document: Any, dataset: str) -> dict[str, Any]:
    if not isinstance(document, dict):
        raise ImportError(f"{dataset}.json must contain an object")
    return document


def _require_timestamp(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ImportError(f"{context} must be a non-empty ISO-8601 timestamp")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ImportError(f"{context} must be a valid ISO-8601 timestamp") from exc
    return value


def parse_envelope(
    document: Any, dataset: str, *, require_supported_version: bool = True
) -> dict[str, str]:
    """Parse common v0.6.0 export metadata for consistency checking."""
    document = _require_object(document, dataset)
    exported_at = _require_timestamp(document.get("exported_at"), f"{dataset}.exported_at")
    plugin_version = document.get("plugin_version")
    session_id = document.get("session_id")
    reason = document.get("reason")
    if not isinstance(plugin_version, str) or not plugin_version.strip():
        raise ImportError(f"{dataset}.plugin_version must be a non-empty string")
    if require_supported_version and plugin_version != SUPPORTED_PLUGIN_VERSION:
        raise ImportError(
            f"{dataset}.plugin_version must be supported version {SUPPORTED_PLUGIN_VERSION!r}"
        )
    if not isinstance(session_id, str) or not session_id.strip():
        raise ImportError(f"{dataset}.session_id must be a non-empty string")
    if not isinstance(reason, str) or not reason.strip():
        raise ImportError(f"{dataset}.reason must be a non-empty string")
    return {
        "exported_at": exported_at,
        "plugin_version": plugin_version,
        "session_id": session_id,
        "reason": reason,
    }


def _require_supported_stats(stats: Any) -> dict[str, dict[str, int]]:
    if not isinstance(stats, dict):
        raise ImportError("character.stats must be an object")
    actual = set(stats)
    expected = set(SKILLS)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise ImportError(f"character.stats skill layout mismatches supported skills; missing={missing}, unknown={unknown}")

    parsed: dict[str, dict[str, int]] = {}
    for skill in SKILLS:
        record = stats[skill]
        if not isinstance(record, dict) or set(record) != {"real_level", "boosted_level", "experience"}:
            raise ImportError(f"character.stats.{skill} must contain exactly real_level, boosted_level, experience")
        real_level = record["real_level"]
        boosted_level = record["boosted_level"]
        experience = record["experience"]
        if not _is_int(real_level) or not 1 <= real_level <= 99:
            raise ImportError(f"character.stats.{skill}.real_level must be an integer from 1 to 99")
        if not _is_int(boosted_level):
            raise ImportError(f"character.stats.{skill}.boosted_level must be an integer")
        if not _is_int(experience):
            raise ImportError(f"character.stats.{skill}.experience must be an integer")
        derived_level = level_from_xp(experience)
        if derived_level != real_level:
            raise ImportError(
                f"character.stats.{skill} level/XP mismatch: real_level={real_level}, XP derives level {derived_level}"
            )
        parsed[skill] = {"real_level": real_level, "experience": experience}
    return parsed


def parse_character(document: Any) -> dict[str, Any]:
    """Return normalized phase-1 character data, excluding temporary boosts."""
    document = _require_object(document, "character")
    account_name = document.get("account_name")
    if not isinstance(account_name, str) or not account_name.strip():
        raise ImportError("character.account_name must be a non-empty string")
    return {"account_name": account_name, "stats": _require_supported_stats(document.get("stats"))}


def parse_quests(document: Any) -> list[str]:
    """Return unique finished quest names, rejecting malformed or duplicate rows."""
    document = _require_object(document, "quests")
    quests = document.get("quests")
    if not isinstance(quests, list):
        raise ImportError("quests.quests must be an array")

    ids: set[str | int] = set()
    names: set[str] = set()
    finished: list[str] = []
    for index, quest in enumerate(quests):
        context = f"quests.quests[{index}]"
        if not isinstance(quest, dict) or set(quest) != {"id", "name", "state"}:
            raise ImportError(f"{context} must contain exactly id, name, state")
        quest_id = quest["id"]
        name = quest["name"]
        state = quest["state"]
        if (not isinstance(quest_id, (str, int)) or isinstance(quest_id, bool) or (isinstance(quest_id, str) and not quest_id.strip())):
            raise ImportError(f"{context}.id must be a non-empty string or integer")
        if not isinstance(name, str) or not name.strip():
            raise ImportError(f"{context}.name must be a non-empty string")
        if state not in QUEST_STATES:
            raise ImportError(f"{context}.state must be one of {sorted(QUEST_STATES)}")
        if quest_id in ids:
            raise ImportError(f"duplicate quest id in export: {quest_id!r}")
        if name in names:
            raise ImportError(f"duplicate quest name in export: {name!r}")
        ids.add(quest_id)
        names.add(name)
        if state == "FINISHED":
            finished.append(name)
    return finished


def parse_diaries(document: Any) -> dict[str, Any]:
    """Return report-only diary aggregates; never interpret task completion as state."""
    document = _require_object(document, "diaries")
    diaries = document.get("diaries")
    if not isinstance(diaries, dict):
        raise ImportError("diaries.diaries must be an object")
    report: dict[str, dict[str, dict[str, Any]]] = {}
    for area, tiers in diaries.items():
        if not isinstance(area, str) or not area.strip() or not isinstance(tiers, dict):
            raise ImportError("diaries areas and tiers must be non-empty strings and objects")
        area_report: dict[str, dict[str, Any]] = {}
        for tier, record in tiers.items():
            if not isinstance(tier, str) or not tier.strip() or not isinstance(record, dict):
                raise ImportError("diary tier records must be objects")
            complete = record.get("complete")
            tasks_done = record.get("tasks_done")
            if not isinstance(complete, bool) or not _is_int(tasks_done) or tasks_done < 0:
                raise ImportError(f"diaries.{area}.{tier} must include boolean complete and non-negative tasks_done")
            tasks = record.get("tasks")
            if tasks is not None and not isinstance(tasks, list):
                raise ImportError(f"diaries.{area}.{tier}.tasks must be an array when present")
            area_report[tier] = {
                "complete": complete,
                "tasks_done": tasks_done,
                "named_tasks_present": isinstance(tasks, list),
            }
        report[area] = area_report
    return report


def _load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise ImportError(f"missing required export dataset: {path.name}") from exc
    except json.JSONDecodeError as exc:
        raise ImportError(f"invalid JSON in {path.name}: {exc.msg}") from exc


def load_export_documents(account_directory: Path) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """Load only phase-1 datasets and identify unparsed/missing optional data."""
    documents = {dataset: _load_json(account_directory / f"{dataset}.json") for dataset in REQUIRED_DATASETS}
    warnings: list[str] = []
    for dataset in OPTIONAL_DATASETS:
        path = account_directory / f"{dataset}.json"
        if dataset == "diaries" and path.is_file():
            documents[dataset] = _load_json(path)
        elif path.is_file():
            warnings.append(
                f"optional {dataset}.json is present but unsupported in phase 1; it was not opened or imported"
            )
        else:
            warnings.append(f"optional {dataset}.json is missing; it was not treated as empty account state")
    return documents, warnings


def _validate_export_consistency(
    documents: dict[str, dict[str, Any]], expected_account_name: str | None, warnings: list[str]
) -> dict[str, dict[str, str]]:
    envelopes = {
        dataset: parse_envelope(
            document, dataset, require_supported_version=dataset in REQUIRED_DATASETS
        )
        for dataset, document in documents.items()
    }
    reference = envelopes["character"]
    for dataset in REQUIRED_DATASETS:
        envelope = envelopes[dataset]
        if envelope["session_id"] != reference["session_id"]:
            raise ImportError(f"mixed export sessions: character and {dataset} have different session_id values")
        if envelope["plugin_version"] != reference["plugin_version"]:
            raise ImportError(f"mixed plugin versions: character and {dataset} disagree")
    diary_envelope = envelopes.get("diaries")
    if diary_envelope is not None:
        if diary_envelope["session_id"] != reference["session_id"]:
            warnings.append("diaries.json is from a different export session; it remains report-only provenance")
        if diary_envelope["plugin_version"] != reference["plugin_version"]:
            warnings.append("diaries.json has a different plugin version; it remains report-only provenance")
    character = parse_character(documents["character"])
    if expected_account_name is not None and character["account_name"].casefold() != expected_account_name.casefold():
        raise ImportError("character.account_name does not match --account-name")
    for dataset in REQUIRED_DATASETS:
        document = documents[dataset]
        account_name = document.get("account_name")
        if account_name is not None and account_name != character["account_name"]:
            raise ImportError(f"mixed account exports: character and {dataset} disagree on account_name")
    diary_document = documents.get("diaries")
    if diary_document is not None:
        diary_account_name = diary_document.get("account_name")
        if diary_account_name is not None and diary_account_name != character["account_name"]:
            warnings.append("diaries.json has a different account_name; it remains report-only provenance")
    return envelopes


def import_runelite_export(
    base_account_state: dict[str, Any],
    export_documents: dict[str, dict[str, Any]],
    *,
    account_directory: Path | None = None,
    expected_account_name: str | None = None,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    """Return an updated deep copy plus provenance. This function performs no I/O."""
    validate_account_state(base_account_state)
    if set(REQUIRED_DATASETS) - set(export_documents):
        raise ImportError("character.json and quests.json are required for phase-1 import")
    import_warnings = list(warnings or [])
    envelopes = _validate_export_consistency(export_documents, expected_account_name, import_warnings)
    character = parse_character(export_documents["character"])
    finished_quests = parse_quests(export_documents["quests"])

    next_state = copy.deepcopy(base_account_state)
    for skill, stat in character["stats"].items():
        next_state["skills"][skill] = stat["real_level"]
        next_state["skill_xp"][skill] = stat["experience"]
    next_state["quests_completed"] = list(dict.fromkeys([*next_state["quests_completed"], *finished_quests]))
    validate_account_state(next_state)

    diary_report: dict[str, Any]
    if "diaries" in export_documents:
        diary_report = {
            "status": "reported_only",
            "freshness": envelopes["diaries"],
            "areas": parse_diaries(export_documents["diaries"]),
        }
    else:
        diary_report = {"status": "missing", "areas": {}}

    import_warnings.append("boosted skill levels were read only for export-shape validation and were not imported")
    import_warnings.append("item containers, equipment, combat achievements, and collection log are unsupported in phase 1")
    return {
        "updated_account_state": next_state,
        "import_report": {
            "phase": "runelite-character-export-phase-1",
            "account_name": character["account_name"],
            "account_directory": str(account_directory) if account_directory else None,
            "datasets": envelopes,
            "imported": {
                "skills": len(character["stats"]),
                "skill_xp": len(character["stats"]),
                "finished_quests": len(finished_quests),
                "quests_added": len(set(next_state["quests_completed"]) - set(base_account_state["quests_completed"])),
            },
            "diaries": diary_report,
            "omitted_private_or_unsupported_fields": [
                "boosted skill levels", "quest steps", "bank", "seed vault", "inventory", "equipment",
                "combat achievements", "collection log", "world and game session state",
            ],
            "warnings": import_warnings,
            "false_inference_flags": {
                "quest_steps_inferred": False,
                "milestones_inferred": False,
                "transport_unlocks_inferred": False,
                "completed_actions_inferred": False,
                "quest_rewards_inferred": False,
                "diary_tiers_mutated": False,
                "diary_task_observations_mutated": False,
                "item_containers_treated_as_empty": False,
            },
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Import phase-1 data from a local RuneLite Character Export v0.6.0 folder.")
    location = parser.add_mutually_exclusive_group(required=True)
    location.add_argument("--account-directory", type=Path)
    location.add_argument("--export-root", type=Path)
    parser.add_argument("--account-name", help="Required with --export-root; checked against character.json.")
    parser.add_argument("--base-state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--output", type=Path, help="Write the import document here instead of stdout.")
    parser.add_argument("--force", action="store_true", help="Allow --output to replace an existing file.")
    args = parser.parse_args()

    try:
        if args.export_root is not None and args.account_name is None:
            raise ImportError("--account-name is required with --export-root")
        if args.account_directory is not None and args.account_name is not None:
            raise ImportError("--account-name is only valid with --export-root")
        if args.output is not None and args.output.exists() and not args.force:
            raise ImportError(f"refusing to overwrite existing output: {args.output}; use --force to replace it")
        directory = resolve_account_directory(
            account_directory=args.account_directory,
            export_root=args.export_root,
            account_name=args.account_name,
        )
        documents, warnings = load_export_documents(directory)
        result = import_runelite_export(
            load_json(args.base_state),
            documents,
            account_directory=directory,
            expected_account_name=args.account_name,
            warnings=warnings,
        )
    except (ImportError, ValueError, OSError) as exc:
        print(f"Import failed: {exc}", file=sys.stderr)
        return 2

    output = json.dumps(result, indent=2) + "\n"
    if args.output is None:
        print(output, end="")
    else:
        args.output.write_text(output, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
