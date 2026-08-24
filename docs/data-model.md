# Data Model

## Fact records

Every record in `data/facts/` is a sourced claim, not a recommendation. A fact may include its identifier, category, verification date, requirements, rewards, costs, outputs, sources, confidence, and validation status.

Facts must not contain route order, subjective priority, or instructions such as "do this early." Those belong in `strategy/`.

## Graph records

`graph/nodes.json` describes selectable goals, activities, and account-state flags. `graph/edges.json` describes relationships.

| Edge type | Meaning |
| --- | --- |
| `requires` | Hard prerequisite. |
| `unlocks` | A completed node makes another capability available. |
| `makes_obtainable` | Enables attempts at an RNG or currency-gated reward without implying acquisition. |
| `alternative` | Another valid way to satisfy the same need. |
| `bypass` | A path removes or meaningfully reduces a conventional requirement. |
| `produces` | An activity creates an item, resource, or state. |
| `improves` | A lasting enhancement without being a strict prerequisite. |

## Account state

An account state holds skill levels, completed quests and actions, transport flags, milestones, gear thresholds, item counts, spendable resources, permanent counters, active passive loops, attention availability, preferences, and discovered drops. Items, spendable resources, and non-spendable counters are distinct so preparation and economic accounting do not silently consume permanent progress such as Kudos.

### Post-tutorial pilot fixture

`tests/fixtures/fresh-account.json` remains the zero-state boundary. `tests/fixtures/new-ironman-post-tutorial.json` is the recommendation pilot's Standard Ironman starting point immediately after completing `Learning the Ropes`: its fixed arrival kit, 25 banked coins, and one quest point are sourced in `data/facts/new-ironman-post-tutorial.json`. The tutorial quest is intentionally not placed in `quests_completed`, because the current progression graph has no normalized Tutorial Island action.

The fixture's skill XP values deliberately remain the evaluator's level-consistent lower bounds, not a literal replay of Tutorial Island XP. Current mechanics force player-selected melee style XP and include variable Wind Strike damage; the account-state schema only accepts one integer XP value per skill. The factual record preserves the fixed event facts and this uncertainty. Its attention window and preferences are fixture policy for exercising the chapter compositor, not claims about a new account or the game.

### Player observations

Observation fields are strict snapshots of what the player recorded, not claims the model can derive. Their absence, `null` value, or nullable subfields mean unknown; they must never become hard action gates, create graph edges, or silently fill an inventory field.

| Field | Captures | Does not imply |
| --- | --- | --- |
| `combat_readiness_observation` | Timestamped combat loadouts, current HP/Prayer, available healing/restoration, emergency teleport availability, and recovery tolerance. | Encounter eligibility, a recommended loadout, or a guaranteed kill. |
| `encounter_observations` | Per-encounter attempt window, successes, elapsed minutes, consumed supplies, deaths, and banking trips. | Future throughput, supply burn, or a route decision. |
| `slayer_task` | A currently observed target and remaining count, plus optional initial count, master, streak, points, and blocked targets. | A new assignment, an eligible master, or a deterministic task path. |
| `unique_item_observations` | Separate current possession, collection-log confirmation, quantity, variant, charges, condition, usability, and reclaimability observations. | That an item is currently usable merely because it was once logged, or vice versa. |
| `sailing_observation` | A timestamped vessel snapshot, observed component tiers and facilities, hull and cargo state, accepted task records, and the last recorded recovery event. | Cargo loss, task rewards, repair costs, future task selection, or Sailing throughput. |
| `perilous_moons_observation` | A recorded run, boss defeat order, dungeon-local supplies, and death/recovery state. Moon equipment remains in `unique_item_observations`. | Chest loot, reclaim fees, future completion, set completion, or encounter readiness. |
| `farming_recurrence_observation` | Generic patch snapshots plus nullable Hespori and anima-patch observations. | Growth since the timestamp, disease outcomes, harvest yield, seed supply, or current readiness. |
| `diary_task_observations` | Optional, player-imported records for canonical diary tasks. Each is one closed `combat`, `rng`, `crop`, `daily`, `charge`, `team`, or `staged` snapshot. | A task milestone, diary claim, tier reward, item, counter, collection-log entry, action eligibility, or graph reachability. |

`analyze_combat_observations.py` may divide explicit successes by explicit elapsed minutes to display a measured rate. It returns `null` when either measurement is missing or elapsed time is zero, and marks all readiness, supply, and collection-log inference as false.

### Practical context for combat quests

`strategy/combat-quest-readiness-contexts.json` is a deliberately small strategy-layer registry for an action that is already factually eligible but has a sourced combat encounter. It consumes only an optional generic combat snapshot and an optional named encounter observation. It can describe `needs_practical_readiness`, `needs_tactical_confirmation`, or `timely_after_observed_encounter`; none changes evaluator eligibility, score, requirements, or action transition. A recorded combat snapshot does not prove a tactic, supplies, survival, competence, or victory. A recorded encounter success is an observation, never a generated result.

`analyze_activity_observations.py` returns deep copies of the three structural observations. Its Moon-equipment view selects existing entries from `unique_item_observations`; it never creates a second possession or collection-log state. It does not advance clocks, infer growth or readiness, create loot, calculate reclaim fees, complete equipment sets, or turn community throughput into facts.

### Diary task imports

`diary_task_observations` is optional so older account snapshots remain valid. When supplied, its keys are checked against the 488 integrated factual task keys and its mode payload is closed. A completed imported task still does not write `milestones`, `completed_actions`, `diary_tiers`, inventory, counters, or graph state. `diary_tiers` remains the sole externally player-confirmed claimed-tier snapshot.

The Wilderness elite three-boss-family task is report-only staged state. Its fixed family list is Callisto/Artio, Venenatis/Spindel, and Vet'ion/Calvar'ion. A diary update invalidation must be explicitly observed, and the model does not retain independent boss-family kill milestones or infer final completion from the stage list.

Only these diary-package action labels have behavior-equivalent canonical aliases:

| Package reference | Canonical action |
| --- | --- |
| `action:claim-ardougne-cloak-current` | `action:claim-ardougne-cloak` |
| `action:ardougne-cloak-monastery-teleport` | `action:ardougne-monastery-teleport` |
| `diary-task:varrock:digsite-pendant-teleport` | `action:digsite-pendant-digsite-teleport` |

Descriptive Museum, Digsite-enchantment, and balloon-travel references remain unmapped because each represents multiple or materially different behaviors.

## Normalized progression actions

`data/progression/actions.json` is the executable bridge between sourced facts and account-state evaluation. Each action cites one or more verified fact records and expresses only hard requirements and observable outcomes. Requirements support nested `all` and `any` groups so alternatives can be represented without flattening them into prose.

The evaluator classifies actions as `blocked`, `needs_preparation`, `eligible`, or `completed`. Hard access gates and item preparation are reported separately. Explicit completed-action IDs prevent a partially imported account snapshot from recommending an unrepeatable quest again. The evaluator does not rank eligible actions; ranking belongs to the strategic scoring layer.

## State transitions

An action transition may apply only sourced, guaranteed effects to a copied account state. Set-like quest, transport, milestone, and item-capability outcomes are deterministic. Named options are required when more than one consumable path is valid so the engine never chooses what to spend on the player's behalf.

Quest XP is reported but does not mutate skill levels because a level-only account snapshot does not reveal the exact XP already held within that level. RNG rewards, variable activity XP, farming yields, timers, and unknown item consumption are also reported or deferred. Applying one action is not route traversal and does not imply that the action was strategically preferred.

## Data maturity

- `verified`: current source checked and entered.
- `needs_revalidation`: source exists but needs a fresh in-game or primary-source check.
- `research_queue`: a candidate model entry that must not drive a recommendation yet.
