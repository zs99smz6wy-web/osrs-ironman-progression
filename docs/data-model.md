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

## Normalized progression actions

`data/progression/actions.json` is the executable bridge between sourced facts and account-state evaluation. Each action cites one or more verified fact records and expresses only hard requirements and observable outcomes. Requirements support nested `all` and `any` groups so alternatives can be represented without flattening them into prose.

The evaluator classifies actions as `blocked`, `needs_preparation`, `eligible`, or `completed`. Hard access gates and item preparation are reported separately. Explicit completed-action IDs prevent a partially imported account snapshot from recommending an unrepeatable quest again. The evaluator does not rank eligible actions; ranking belongs to the strategic scoring layer.

## Data maturity

- `verified`: current source checked and entered.
- `needs_revalidation`: source exists but needs a fresh in-game or primary-source check.
- `research_queue`: a candidate model entry that must not drive a recommendation yet.
