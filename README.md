# OSRS Ironman Progression

An evidence-backed, account-state-aware research project for Old School RuneScape Ironman progression.

This repository does **not** begin by prescribing a single linear route. It first records verifiable game facts, models their dependencies and alternatives, and keeps strategic judgement separate. A future route should be generated from that model and explain why a recommendation is timely for a specific account.

## Design principles

- Build a powerful, varied Ironman account without optimizing the game out of the game.
- Prefer durable convenience, transportation, resource pipelines, and multi-output activities over isolated experience grinds.
- Treat collection-log progress as useful only when its reward has material account value.
- Model questing, training, shops, minigames, bossing, and monster drops as alternative or bypass paths where appropriate.
- Track AFK and passive progression as a parallel lane, with clear attention and safety expectations.
- Keep time-sensitive factual claims cited, dated, and independently reviewable.

## Repository map

| Area | Purpose |
| --- | --- |
| `data/facts/` | Source-backed facts only: requirements, rewards, rates, access, and mechanics. |
| `data/schemas/` | JSON schemas and controlled vocabularies for factual records. |
| `data/progression/` | Normalized, source-linked hard requirements and account outcomes. |
| `graph/` | Dependency, alternative, bypass, and account-state graph records. |
| `strategy/` | Explicitly subjective scoring, timing, diversity, and route-generation rules. |
| `research/` | Source registry, validation status, and acquisition backlog. |
| `scripts/` | Local validation tooling. |
| `route/` | Reserved for generated, explainable routes; intentionally not populated yet. |

## Current status

The research foundation and first executable pilot are in place. The pilot can evaluate a small verified set of quests, transport unlocks, passive loops, and activities against an account snapshot. It is a starting dataset, not a final route or exhaustive fact database.

## Validation

Run:

```powershell
python scripts/validate_data.py
python scripts/evaluate_progression.py graph/account-state.example.json
python scripts/score_candidates.py graph/account-state.example.json
python scripts/apply_action.py graph/account-state.example.json action:the-restless-ghost
python scripts/analyze_dependencies.py graph/account-state.example.json --goal action:fossil-island-access --include-preparation --json
python scripts/analyze_cash_commitments.py graph/account-state.example.json --json
python scripts/analyze_passive_status.py graph/account-state.example.json --json
python scripts/transfer_kingdom_coffer.py path/to/account-state.json deposit 10000
```

The validator checks factual record shape, source references, normalized action links, transitions and predicates, graph endpoints, and the firewall between factual and strategic directories. The evaluator separates blocked gates, missing preparation, eligible actions, and completed actions. The scorer compares only eligible actions with strategic annotations and explicitly lists eligible factual actions that remain unscored. The transition tool applies one eligible action to an in-memory copy and prints the resulting state. The dependency analyzer explains the full modeled prerequisite closure for one goal while preserving alternatives and unresolved external inputs. The cash analyzer orders declared purchases by deadline and reports cumulative shortfalls without selecting an earning method. The passive-status analyzer reports permanent loop establishment separately from player-recorded `recurring_observations`; it preserves supplied states and timestamps and never advances timers, infers completion, or grants outputs. Account snapshots record the highest confirmed claimed tier for every achievement-diary region; tier predicates do not infer task readiness, and transitions cannot downgrade a confirmed tier. The Kingdom coffer simulator validates an unlocked Managing Miscellania state and returns a copied state after one exact deposit or withdrawal, enforcing the 5,000,000-coin cap before `Royal Trouble` and the 7,500,000-coin cap after it. It does not infer wages, approval, elapsed time, or collection output. None of these tools generates a route or writes an account snapshot.
