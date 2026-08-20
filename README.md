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
| `graph/` | Dependency, alternative, bypass, and account-state graph records. |
| `strategy/` | Explicitly subjective scoring, timing, diversity, and route-generation rules. |
| `research/` | Source registry, validation status, and acquisition backlog. |
| `scripts/` | Local validation tooling. |
| `route/` | Reserved for generated, explainable routes; intentionally not populated yet. |

## Current status

The initial foundation is in place with a small, validated factual seed covering transportation, Hunter Rumours, Wintertodt, Tithe Farm, Guardians of the Rift, Mage Training Arena, and Sailing/Wyrmscraig research status. It is a starting dataset, not a final route or exhaustive fact database.

## Validation

Run:

```powershell
python scripts/validate_data.py
```

The validator checks factual record shape, source references, graph endpoints, and the firewall between factual and strategic directories.
