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
| `alternative` | Another valid way to satisfy the same need. |
| `bypass` | A path removes or meaningfully reduces a conventional requirement. |
| `produces` | An activity creates an item, resource, or state. |
| `improves` | A lasting enhancement without being a strict prerequisite. |

## Account state

An account state holds skill levels, completed quest flags, transport flags, gear thresholds, stockpiles, active passive loops, attention availability, and discovered drops. It is deliberately separate from game facts so the same graph can be evaluated for different accounts.

## Data maturity

- `verified`: current source checked and entered.
- `needs_revalidation`: source exists but needs a fresh in-game or primary-source check.
- `research_queue`: a candidate model entry that must not drive a recommendation yet.
