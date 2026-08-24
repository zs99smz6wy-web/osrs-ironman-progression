# New Ironman Baseline

`tests/fixtures/new-ironman-post-tutorial.json` is the canonical starting input for a newly created standard Ironman immediately after completing current Tutorial Island, now tracked as `Learning the Ropes`.

It is deliberately different from `tests/fixtures/fresh-account.json`. The latter remains an artificial zero-state boundary for evaluator tests; it owns no tools, food, runes, coins, transport, or quest state. It is not the guide's starting account.

The canonical fixture includes only the fixed Tutorial completion kit, 25 banked coins, one quest point, and guaranteed whole-XP tutorial actions. `axe` and `pickaxe` are normalized availability aliases for the confirmed bronze tools; they do not add a second physical item. Fractional Smithing and Magic XP, combat-style/damage-dependent XP, and all optional extra Tutorial training are documented in `data/facts/new-ironman-post-tutorial.json` but not rounded into the integer snapshot.

The fixture does not claim mainland tutor armour, Adventure Paths, a modeled quest completion, transport, diary tier, passive system, action history, timer, drop, combat readiness, or player-selected location. A real account export may add observed state after this boundary; the mature `On That Cab` account is never a route input or fixture.
