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

## Deliberate phase boundary

Bank, seed vault, inventory, equipment, combat achievements, and collection log are not parsed or opened by phase 1. Their presence, stale metadata, or malformed contents cannot block this import; a missing file means only that it was unavailable to the plugin, never that the account owns nothing. Character and quest exports must agree on their supported plugin version and session ID; optional diary data is report-only provenance.

The importer rejects malformed required data, duplicate quest IDs/names, unknown skill layouts, and permanent-level/XP disagreement. It returns JSON on stdout by default, or writes only to a new path unless `--force` is explicit.

## Privacy policy

The workflow is local-file based. It requires neither Jagex nor RuneLite credentials, cookies, API keys, public hiscores, nor the RuneLite configuration directory. Treat exports as private account data: keep them outside version control, pass the account folder path locally, and share only the generated report or a deliberately redacted state document when collaboration needs it.
