# Passive, AFK, and Economy Windows

This is a strategy-layer timing dossier. It reuses verified mechanics and existing
actions, but it does not select a universal route or money-maker. A window is a
candidate when its rewards serve a declared account need, nearby work, or a useful
low-attention interval.

## Shared boundaries

- Hard access comes from factual records and normalized actions.
- `passive_loops` records established access; it does not prove that a crop, nest,
  Kingdom collection, or Tears attempt is ready.
- `recurring_observations` and `kingdom_observation` require a player-confirmed
  state and observation time. A passed timer does not create rewards or completion.
- AFK means player-present and safe. No window assumes unattended overnight play.
- Random drops, seed packs, nests, and variable outputs create opportunities and
  stop checks, not guaranteed route transitions.

## Birdhouses

- **ID and gates:** `action:birdhouse-loop`; fact `birdhouse-loop`. Membership,
  Fossil Island access, Crafting 5, Hunter 5, and the Ironman clockwork setup
  (Construction 25 and a Crafting table 2) are factual gates.
- **Window:** Establish the loop once Fossil Island access and clockwork inputs are
  available, especially before a travel episode that already visits the island.
  Re-enter on a player-observed ready state, normally after the roughly 50-minute
  seed cycle.
- **Purpose:** Passive Hunter/Crafting progress, nests, seeds, and bird meat can
  support the account. Value rises when the account wants Hunter levels, Farming
  seeds, or a low-attention companion between active sessions.
- **Stop/re-entry:** Stop collection when the current cycle is complete or the
  active session has another declared objective. Re-enter when four usable
  clockworks, logs, seeds, and an observed ready state are available.
- **Compatibility:** Strong passive companion; active collection and reset still
  require travel and inventory attention. No intrinsic combat risk.
- **Boundary:** Do not infer nest quantity, seed value, or completion from elapsed
  time alone.

## Giant seaweed

- **ID and gates:** Fact `giant-seaweed-passive-loop`. Membership, Bone Voyage,
  Farming 23, two patches, seed dibber, fishbowl helmet, diving apparatus, and a
  seaweed spore per patch are factual gates. Compost and 200 numulite protection
  per patch are optional inputs with different risk/cost tradeoffs.
- **Window:** Establish it when Fossil Island travel and underwater access already
  fit the account, or when soda ash is a named future Crafting bottleneck. A patch
  grows for about 40 minutes, so it pairs naturally with another active objective.
- **Purpose:** Giant seaweed supports soda ash and Crafting supply preparation;
  protection trades numulite for lower disease risk. Cooking 51 makes the soda-ash
  conversion deterministic, but does not gate planting or harvesting.
- **Stop/re-entry:** Stop after the current harvest, a declared soda-ash supply
  boundary, or exhausted spores. Re-enter after a player-observed ready patch and
  confirmed spores, tools, and desired protection choice.
- **Compatibility:** Strong passive companion when Fossil Island is already in the
  account's travel graph; active underwater planting and harvesting are required.
- **Boundary:** Do not assume a fixed harvest, spore rate, or disease outcome.

## Farming contracts

- **ID and gates:** Fact `farming-contracts-passive-loop`. Farming Guild access and
  the selected tier are factual gates: Easy 45, Medium 65, Hard 85. The assigned
  crop's Farming requirement and its seeds or sapling are also hard per-contract
  checks.
- **Window:** Use contracts when routine patch work can satisfy them without
  displacing a more valuable crop, or when seed packs address a named future
  Farming supply need. Higher tiers become candidates at their access levels, not
  automatic training targets.
- **Purpose:** A contract adds a seed pack to normal crop XP and harvest outputs.
  It is most useful when patch routing, seed supply, and a desired pack tier align.
- **Stop/re-entry:** Stop after the current contract, seed-pack target, or Farming
  threshold. Re-enter when a new assignment, required seed, and patch timing are
  observed. Do not assume an assignment from the calendar; only one contract is
  active and crop durations vary from minutes to days.
- **Compatibility:** Excellent long-horizon passive companion; patch collection,
  assignment, and completion are active interactions. Crop disease is the relevant
  failure state, not combat.
- **Boundary:** Seed-pack contents and crop survival remain variable. A pre-grown
  crop can satisfy a matching contract, but no contract is completed merely by
  waiting.

## Tears of Guthix

- **ID and gates:** Fact `tears-of-guthix`. The quest is required for normal access;
  later games require seven full days and at least 100,000 experience or one quest
  point since the previous completed game. The first game is exempt from the
  progress gate.
- **Window:** Treat the first eligible game and each later observed cooldown as a
  recurring catch-up window, especially when the lowest eligible skill benefits
  from automatic targeting. The Hard Lumbridge & Draynor Diary adds 10% only after
  its factual completion is recorded.
- **Purpose:** Fill the account's lowest eligible skill without choosing the skill
  manually. It can smooth a threshold, but should not be used to manufacture a
  fixed training route or to delay a more valuable quest XP decision.
- **Stop/re-entry:** The bounded stop is the completed session and awarded XP.
  Re-enter only after the player confirms the cooldown/progress conditions and a
  current session is available.
- **Compatibility:** Low repetition and no minigame damage, but the collection
  session is active: streams move every 9.6 seconds and green tears must be avoided.
- **Boundary:** XP amount, target skill, and movement outcome are variable; elapsed
  time alone does not award the experience.

## Kingdom / Managing Miscellania

- **ID and gates:** Fact `throne-of-miscellania` establishes Throne of Miscellania,
  its Heroes' Quest and Fremennik Trials dependencies, 75% approval requirement,
  10,000-coin coffer reward, and Managing Miscellania unlock. Fact
  `royal-trouble` covers the separate extension and its combat/skill gates.
- **Window:** The first window is the point at which the quest chain, required
  items, 75% approval method, and funding can be completed without crowding out a
  higher-value purchase. The recurring loop becomes a candidate only after access
  and a funded coffer are established.
- **Purpose:** Kingdom is route-shaping infrastructure: it converts recurring
  account funding into selected resource outputs while the player does other
  content. Worker assignments are a strategy choice tied to a named supply need,
  not a permanent default.
- **Stop/re-entry:** Stop the setup episode after access, coffer funding, and the
  intended worker state are player-confirmed. Re-enter for collection or changes
  only with a current `kingdom_observation` containing approval, assignments,
  pause state, and observation time.
- **Compatibility:** Passive between active collection and approval actions; it is
  not an AFK activity to be monitored by inferred elapsed time. It competes with
  early GP, quest-chain, combat, and travel costs.
- **Boundary:** Do not calculate approval decay, daily deductions, elapsed output,
  or collection results from timestamps. Do not claim Kingdom is worthwhile before
  identifying the resource need and cash commitment.

## Suitable AFK companions

These are companion candidates, not a ranked activity list. Select one only when
the account has a named need and a player-present attention window.

| Candidate | Existing record/action | Best companion use | Stop boundary |
| --- | --- | --- | --- |
| Birdhouses | `birdhouse-loop` / `action:birdhouse-loop` | Offline timer between active episodes; nests, seeds, Hunter/Crafting progress | Current cycle collected and reset, or inputs/attention unavailable |
| Giant seaweed | `giant-seaweed-passive-loop` | Crafting supply preparation during other Fossil Island-compatible work | Harvest or declared soda-ash boundary |
| Farming contracts | `farming-contracts-passive-loop` | Patch rounds with seed-pack purpose | Current contract or seed target complete |
| Tears | `tears-of-guthix` | Weekly catch-up XP after observed eligibility | One completed game |
| Motherlode Mine | `motherlode-mine` / `action:motherlode-mine` | Player-present low-attention Mining plus a defined storage reward | Coal bag, gem bag, Prospector, or current Mining target |
| Shooting stars | `shooting-stars-observed-session` / `action:shooting-stars` | Player-present low-attention Mining when a star is actually observed | Observed star/session ends or safety changes |
| Fishing/woodcutting | AFK packages and scored actions | Food/log supply or a short low-attention skill window | Spot, supplies, capacity, or stated skill need ends |
| Safe combat | `safe-combat-training-observed-session` / `action:safe-combat-training` | Player-present combat XP when local safety and readiness are observed | Session, safety, or readiness observation changes |

The companion lane must not hide travel, banking, food, tool, aggression, or
survival requirements. `true_afk` applies to recurring growth between interactions;
player-present low-attention methods remain bounded observations.

## Route-shaping cash and economic infrastructure

- **Cash policy:** GP is a deadline-backed resource. First record the purchase,
  fee, deposit, or material deadline; then compare eligible methods by what else
  they advance. No method is globally optimal.
- **Existing comparison set:** Economic facts cover Agility Pyramid, wealthy-citizen
  valuables, Giants' Foundry commissions, silk, blackjacking, Sailing bounties,
  Sailing salvaging, Port Roberts stalls, and concrete cash commitments. Existing
  comparison context is `research/economic-method-comparison.json` and the policy is
  `strategy/economic-policy.md`.
- **Infrastructure windows:** A cash window may support an identified purchase such
  as house ownership, a POH upgrade, utility storage, quest supplies, Kingdom
  funding, runes, or the 15,000-coin Skiff benchmark at 15 Sailing. Sailing entry
  itself does not imply pre-funding a Skiff or selecting an income method.
- **Selection test:** Eliminate methods blocked by factual gates; prefer a method
  whose current outputs also advance the active skill, supply, gear, access, or
  attention goal; subtract detour, danger, repetition, and supply pressure; retain
  multiple candidates when current cash, skills, or preference are unknown.
- **Stop/re-entry:** Stop when the named cash deadline is met, the purchase is made,
  or the method no longer advances the declared account need. Re-enter for a new
  observed deadline, purchase, material shortfall, or changed attention window.
- **Boundary:** Variable loot, rates, failures, alchs, and market-like values must
  remain observations or sourced ranges. Do not convert a benchmark, community
  guide, or one successful method into a universal route transition.

## Source and confidence boundary

Primary factual reuse comes from `data/facts/afk-passive.json`,
`data/facts/kingdom-quest-chain.json`, `data/facts/economic-bottlenecks.json`,
the existing AFK method packages, and `research/sailing-economics-timing.md`.
Strategy reuse comes from `strategy/afk-and-passive-model.md`,
`strategy/economic-policy.md`, `strategy/sailing-economics-contexts.json`, and
the scored candidate records. Stronger timing claims still require a declared
account snapshot, current observations, and the specific downstream purpose.
