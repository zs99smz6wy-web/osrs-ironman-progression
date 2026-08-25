# Content Window Research

This directory maps major account objectives to the shared contract in `strategy/content-window-contract.md`.

Domain files remain strategy research. They may reuse verified repository facts but do not change eligibility, apply account transitions, select a route, or write guide steps.

## Domain split

- `quest-unlocks-and-xp.md`
- `utility-minigames.md`
- `pvm-and-gear.md`
- `passive-afk-and-economy.md`
- `milestone-skeleton.md` after domain review
- `evaluator-slice.md`

## Machine-readable slice

`strategy/content-window-catalog.json` maps a bounded set of normalized actions to the default objective profile. `scripts/evaluate_content_windows.py` preserves factual action status while adding purpose, attention, ideal-trigger, stop, and re-entry classifications.

Run the default active opening comparison with:

```text
python scripts/evaluate_content_windows.py tests/fixtures/fresh-account.json strategy/default-opening-decision-context.json
```

The output is comparison evidence. It never selects or applies a route.

## Scope rule

Record route-shaping objectives, not every activity. An objective belongs here when at least one is true:

- it permanently unlocks content or transportation;
- its XP can skip a meaningful training threshold;
- its reward changes long-term inventory, banking, gathering, combat, or supply handling;
- it has a narrow ideal timing window;
- it creates an important deterministic or random bypass;
- it is a recurring passive system worth starting early;
- it is major PvM or skilling content the project intends the player to enjoy at an appropriate stage.

Prefer concise tables. Link to existing facts and timing packages instead of repeating mechanics.
