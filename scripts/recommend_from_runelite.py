"""Import a local RuneLite Character Export and compose recommendation options."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from compose_recommendation_chapter import (
    AFK_MODES,
    DEFAULT_ACTIVE_LIMIT,
    DEFAULT_AFK_LIMIT,
    DEFAULT_PREPARATION_LIMIT,
    DEFAULT_QUEST_XP_LIMIT,
    compose_recommendation_chapter,
)
from analyze_quest_xp_timing import DEFAULT_EDGES, DEFAULT_NODES
from evaluate_progression import DEFAULT_ACTIONS, DEFAULT_STATE, load_json
from import_runelite_export import (
    ImportError as RuneLiteImportError,
    import_runelite_export,
    load_export_documents,
    resolve_account_directory,
)
from score_candidates import DEFAULT_CANDIDATES


def recommend_from_runelite(
    base_account_state: dict[str, Any],
    export_documents: dict[str, dict[str, Any]],
    actions_document: dict[str, Any],
    candidates_document: dict[str, Any],
    nodes_document: dict[str, Any],
    edges_document: dict[str, Any],
    *,
    account_directory: Path | None = None,
    expected_account_name: str | None = None,
    warnings: list[str] | None = None,
    active_limit: int = DEFAULT_ACTIVE_LIMIT,
    afk_limit: int = DEFAULT_AFK_LIMIT,
    preparation_limit: int = DEFAULT_PREPARATION_LIMIT,
    quest_xp_limit: int = DEFAULT_QUEST_XP_LIMIT,
    afk_mode: str = "low_attention",
    include_state: bool = False,
) -> dict[str, Any]:
    """Run the importer and compositor in order without adding policy or parsing."""
    imported = import_runelite_export(
        base_account_state,
        export_documents,
        account_directory=account_directory,
        expected_account_name=expected_account_name,
        warnings=warnings,
    )
    chapter = compose_recommendation_chapter(
        imported["updated_account_state"],
        actions_document,
        candidates_document,
        nodes_document,
        edges_document,
        active_limit=active_limit,
        afk_limit=afk_limit,
        preparation_limit=preparation_limit,
        quest_xp_limit=quest_xp_limit,
        afk_mode=afk_mode,
    )
    result: dict[str, Any] = {
        "import_report": imported["import_report"],
        "recommendation_chapter": chapter,
    }
    if include_state:
        result["updated_account_state"] = imported["updated_account_state"]
    return result


def _write_or_print(document: dict[str, Any], output: Path | None, force: bool) -> None:
    if output is not None and output.exists() and not force:
        raise RuneLiteImportError(
            f"refusing to overwrite existing output: {output}; use --force to replace it"
        )
    rendered = json.dumps(document, indent=2) + "\n"
    if output is None:
        print(rendered, end="")
    else:
        output.write_text(rendered, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import local RuneLite data and compose bounded recommendation options."
    )
    location = parser.add_mutually_exclusive_group(required=True)
    location.add_argument("--account-directory", type=Path)
    location.add_argument("--export-root", type=Path)
    parser.add_argument("--account-name", help="Required with --export-root.")
    parser.add_argument("--base-state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--active-limit", default=DEFAULT_ACTIVE_LIMIT, type=int)
    parser.add_argument("--afk-limit", default=DEFAULT_AFK_LIMIT, type=int)
    parser.add_argument("--preparation-limit", default=DEFAULT_PREPARATION_LIMIT, type=int)
    parser.add_argument("--quest-xp-limit", default=DEFAULT_QUEST_XP_LIMIT, type=int)
    parser.add_argument("--afk-mode", choices=AFK_MODES, default="low_attention")
    parser.add_argument("--include-state", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    try:
        if args.export_root is not None and args.account_name is None:
            raise RuneLiteImportError("--account-name is required with --export-root")
        if args.account_directory is not None and args.account_name is not None:
            raise RuneLiteImportError("--account-name is only valid with --export-root")
        directory = resolve_account_directory(
            account_directory=args.account_directory,
            export_root=args.export_root,
            account_name=args.account_name,
        )
        documents, warnings = load_export_documents(directory)
        result = recommend_from_runelite(
            load_json(args.base_state),
            documents,
            load_json(DEFAULT_ACTIONS),
            load_json(DEFAULT_CANDIDATES),
            load_json(DEFAULT_NODES),
            load_json(DEFAULT_EDGES),
            account_directory=directory,
            expected_account_name=args.account_name,
            warnings=warnings,
            active_limit=args.active_limit,
            afk_limit=args.afk_limit,
            preparation_limit=args.preparation_limit,
            quest_xp_limit=args.quest_xp_limit,
            afk_mode=args.afk_mode,
            include_state=args.include_state,
        )
        _write_or_print(result, args.output, args.force)
    except (RuneLiteImportError, ValueError, OSError, json.JSONDecodeError) as error:
        print(f"Recommendation pipeline failed: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
