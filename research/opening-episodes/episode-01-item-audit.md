# Episode 01 Canonical Item Audit

## Boundary

Applies only to the Tutorial-exit -> Lumbridge local relay -> Lumbridge Castle
bank candidate. It does not define later withdrawals or route order.

## Starting state

Use `tests/fixtures/new-ironman-post-tutorial.json` for account-wide ownership.
Do not double-count its generic `axe` / `pickaxe` capability keys as physical
items in addition to `bronze_axe` / `bronze_pickaxe`.

Physical Tutorial item IDs are `bronze_axe`, `bronze_pickaxe`, `tinderbox`,
`small_fishing_net`, `shrimps`, `bronze_dagger`, `bronze_sword`,
`wooden_shield`, `shortbow`, `bronze_arrow`, `air_rune`, `mind_rune`, `bucket`,
`pot`, `bread`, `water_rune`, `earth_rune`, and `body_rune`.

Coins belong in `resources.coins`, not `items.coins`. The fixture records 25
account-wide coins; the factual baseline says they begin banked.

## Episode deltas

| ID | Direction | Quantity | Fate and boundary |
| --- | --- | ---: | --- |
| `spade` | acquired | 1 | Reusable; bank after the first X Marks dig. `functional_spade` is a research capability label, not the account item ID. |
| `hammer` | acquired | 1 | Reusable; bank for Daddy's Home. |
| `chisel` | acquired | 1 | Reusable durable utility. |
| `air_talisman` | received | 1 | Rune Mysteries start output; presence alone cannot prove stage. |
| `treasure_scroll_first_clue` | received then removed | 1 | Temporary X Marks item; absent from end state. |
| `treasure_scroll_second_clue` | received | 1 | End-state item; stage still needs player confirmation. |
| `coins` | spent | 5 listed baseline | Store in `resources.coins`; observe shop total and pickpocket loot before recording the end quantity. |

## Naming and observation boundaries

- Use `spade` in canonical account state. `functional_spade` only distinguishes
  valid spades inside the partial-quest package.
- Do not introduce `normal_logs` or `logs`; this episode acquires no logs.
- Do not introduce `nails`; Daddy's Home materials are outside this episode.
- Do not convert either diary interaction into XP or fixed coins. Pickpocket
  loot is variable and both credits require player confirmation.
- Do not model the four starter-gear sales. Their 38-coin total remains a
  derived live-validation gap.
- RuneLite can confirm point-in-time bank/inventory contents, not the dialogue
  or replacement events that produced the two partial quest states.
