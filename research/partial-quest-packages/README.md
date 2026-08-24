# Partial quest research packages

These packages resolve the gap between quest-level facts and player-readable execution segments. They describe stable quest checkpoints that can support macroquesting without treating a started or partially progressed quest as completed.

## Boundary

- Facts and source-backed observations belong here.
- Route order, efficiency scores, lamp choices, and recommendations do not.
- A checkpoint is not account state merely because it appears in a package.
- Promotion to a normalized milestone requires a stable checkpoint, an explicit completion observation, and a separately reviewed progression action.
- Quest completion remains a `quest_completed` observation. Partial checkpoints never satisfy it.
- RuneLite or Character Exporter support must be stated as observed capability, not assumed.

## Checkpoint resolution

Each checkpoint uses one of three observation classes:

- `quest_list`: reliably observable as quest completion only.
- `inventory_or_equipment`: an item can support the checkpoint, but possession alone may not prove the quest stage unless the package says it is exclusive and sufficient.
- `player_confirmation`: the guide must ask the player to confirm the interaction or stage.

The `promotion.status` field records whether central integration has reviewed a checkpoint for durable account state. `research_only` is the default. `eligible_for_milestone` means the checkpoint is stable enough to consider, not that it has already been normalized.

The package schema is `research/package-schemas/partial-quest-package.schema.json`. Dossiers in this directory preserve the detailed source review used to build compact JSON packages.
