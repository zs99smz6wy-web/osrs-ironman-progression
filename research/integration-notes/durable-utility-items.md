# Durable Utility-Item Timing Integration

This pass reconciles the existing Tithe Farm, Motherlode Mine, Mage Training Arena, and Last Man Standing packages with a single factual catalog for herb sack, seed box, gem bag, coal bag, and rune pouch. It contains no scoring, route selection, or recommendation integration.

## Production-ready actions

- `action:buy-tithe-herb-sack`: 250 observed Tithe Farm points, Farming 34, and unboostable Herblore 58.
- `action:buy-slayer-herb-sack`: 750 observed Slayer reward points and unboostable Herblore 58.
- `action:buy-tithe-seed-box`: 250 observed Tithe Farm points and Farming 34.
- `action:buy-coal-bag` and `action:buy-gem-bag`: 100 observed golden nuggets and Mining 30.
- `action:buy-mta-rune-pouch`: the four observed Pizazz balances at 150 / 150 / 1,500 / 200.
- `action:buy-slayer-rune-pouch`: 750 observed Slayer reward points.

Each is a confirmed fixed purchase action. None creates points, nuggets, Pizazz, Slayer points, items, or minigame completion from a plan or an observation snapshot.

## Observation Contract

`items` records durable ownership only after a confirmed purchase or conservative importer result. `resources` holds explicitly reported spendable balances. For minigames, the matching optional `minigame_activity_observations` snapshot can record the same balance and confirmed shop purchase, but it remains report-only: the evaluator never promotes it into `resources` or ownership.

The LMS direct Rune pouch path is factual but intentionally has no executable action. It additionally needs an explicit 48-hour member-playtime observation and an observed available Justine shop row; neither can be inferred from LMS points, an account level, or a prior match. A later observation-aware predicate can integrate that path without changing the facts here.

## Deliberate Gaps

- Stored contents, open/closed state, refills, automatic pickups, equipped cape effects, and all later use remain observations.
- The silklined Herb sack and any Gem bag upgrade are not normalized in this pass.
- No route advice is encoded from Ironman guides. The existing guide material remains strategy-only context for a later scoring layer.
