# Account Ingestion

## RuneLite Character Export phase 1

This repository can import a local [DZWNK/Character-Export](https://github.com/DZWNK/Character-Export) v0.6.0 snapshot. The upstream [implementation](https://github.com/DZWNK/Character-Export/blob/main/src/main/java/com/dzwnk/exporter/CharacterStateExporterPlugin.java) and [README](https://github.com/DZWNK/Character-Export/blob/main/README.md) were checked on 2026-08-24.

The upstream exporter builds the `stats` object with RuneLite `Skill.getName()`. RuneLite's [Skill enum](https://github.com/runelite/runelite/blob/master/runelite-api/src/main/java/net/runelite/api/Skill.java) uses title-case names, including `Runecraft` and `Sailing`; phase 1 requires that exact full layout.

The default Windows location is:

```text
%USERPROFILE%\\.runelite\\character-exporter\\<sanitized-account-name>\\
```

The folder-name rule is exactly upstream's replacement of each character outside `[A-Za-z0-9_- ]` with `_`.

Phase 1 reads `character.json` and `quests.json`; it reports `diaries.json` without changing diary state. It imports every supported permanent `real_level` and XP, including Sailing, only after proving the canonical XP table derives the exported level. Boosted levels are deliberately omitted.

Only quest records whose state is exactly `FINISHED` are added to `quests_completed`. In-progress quests, quest steps, quest rewards, action history, milestones, and transportation are never inferred.

`diaries.json` is evidence only: area/tier completion, task count, named-task presence, and export provenance remain in `import_report`. Its older session or plugin version produces a warning instead of blocking the import. The importer never changes `diary_tiers` or diary-task observations.

## Item containers

When present, structurally valid, version-compatible, and from the same export session as `character.json`, `bank.json`, `seed_vault.json`, `inventory.json`, and `equipment.json` are imported through the versioned [production resolver](../data/import/runelite-item-resolver.v1.json). The importer aggregates only stable numeric RuneLite item IDs across those distinct containers, then applies the resolver's `sum`, `presence`, or variant `max` rule. Item display names are report-only and are never used to infer identity.

Observed resolved quantities merge conservatively with the base snapshot using the larger value; missing keys are never zeroed. Mismatched, stale-session, malformed, or unavailable containers emit warnings and are omitted rather than treated as empty. The import report lists resolved values, unmapped exported IDs/names, and non-container model keys that remain unresolved. Equipment establishes only observed physical possession for that session, not usability, charges, or reclaimability.

## Deliberate phase boundary

Combat achievements and collection log are not parsed or opened by phase 1. Their presence, stale metadata, or malformed contents cannot block this import; a missing file means only that it was unavailable to the plugin, never that the account owns nothing. Character and quest exports must agree on their supported plugin version and session ID; optional diary data is report-only provenance.

The importer rejects malformed required data, duplicate quest IDs/names, unknown skill layouts, and permanent-level/XP disagreement. It returns JSON on stdout by default, or writes only to a new path unless `--force` is explicit.

## One-command recommendation pipeline

`recommend_from_runelite.py` accepts the same account-directory forms as the importer and then passes the importer's copied state directly into the existing recommendation compositor. It emits only `import_report` and `recommendation_chapter` by default; add `--include-state` when the updated state is deliberately needed. Limits and `--afk-mode` match the compositor. Output goes to stdout unless `--output` is supplied, and an existing output requires `--force`.

The pipeline adds no account inference or route policy: missing containers, diary claims, transport, quest steps, timers, random outputs, combat wins, action completion, and route selection remain outside its boundaries.

## Privacy policy

The workflow is local-file based. It requires neither Jagex nor RuneLite credentials, cookies, API keys, public hiscores, nor the RuneLite configuration directory. Treat exports as private account data: keep them outside version control, pass the account folder path locally, and share only the generated report or a deliberately redacted state document when collaboration needs it.
