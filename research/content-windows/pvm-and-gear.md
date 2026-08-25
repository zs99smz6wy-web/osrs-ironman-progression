# PvM And Gear Content Windows

`id`: `content-window:pvm-and-gear`  
`domain`: PvM and combat-gear progression  
`status`: strategy research; no route selected

This is a timing layer over verified mechanics. A hard gate only establishes
access. Readiness is a player observation, and an RNG item changes the account
only after it is observed.

## Major PvM

| Objective | Normalized records | Hard earliest access | Readiness observations | Ideal-window candidate | Stop / re-entry | Risks and missing coverage |
| --- | --- | --- | --- | --- | --- | --- |
| Royal Titans | `action:royal-titans`; `pvm-readiness-core-activities`; [readiness package](../pvm-readiness/royal-titans.json) | Members; no formal quest, skill, or combat gate. The normal dungeon route has no stated gate; the shortcut and charged amulet are optional access paths. | Selected multi-style and barrier response; supplies; travel, exit, recovery, and optional duo plan; named learning or reward purpose. | Enter when learning the encounter or when a still-unowned targeted reward, pages, or its utility has a declared use. It is not an opening requirement. | Stop when the stated learning, reward, page, or collection objective is satisfied or the plan is no longer acceptable. Re-enter for a new explicit objective with a current plan. | High attention and recovery risk; duo contribution and all loot are variable. No universal gear, supply, trip, kill-count, or target-order claim exists. |
| Perilous Moons quest | `action:perilous-moons-quest`; `perilous-moons-readiness`; [readiness package](../pvm-readiness/perilous-moons.json) | Children of the Sun; Twilight's Promise; 48 Slayer, 20 Hunter, 20 Fishing, 20 Runecraft, and 10 Construction. | Melee-weakness response; glyph and special-mechanic plan; acceptable retreat/recovery plan. Neypotzli food and potions are observed in-run resources, not banked supplies. | Strong when its fixed quest XP and permanent access are useful and the account is ready to enjoy the encounters. Completion unlocks repeatable Moons, Lunar Chest access, Neypotzli, and lesser-nagua task eligibility. | Stop the quest window at completion. Re-enter the repeatable activity only for a declared practice, chest, equipment, or collection goal. | Encounters, chest contents, equipment, and duplicate-protection state remain observed. No set, chest count, external setup, or numeric readiness target is selected. |
| Repeatable Moons of Peril | `action:moons-of-peril`; `perilous-moons-readiness` | Perilous Moons completed; defeat at least one Moon in a run before chest loot. | The quest-window observations, plus a current reason to pursue the specific reward group. | Best evaluated separately from quest completion: enter when an equipment group's role is currently useful, not merely because the chest is unlocked. | Stop when the selected reward or session boundary is met; re-enter when a later gear role, practice goal, or collection goal is still useful. | Unique equipment is RNG, with only within-set duplicate protection. Armour degrades; repair burden and comparative value are not modeled. |
| Barrows | `action:barrows`; `pvm-readiness-core-activities`; [readiness package](../pvm-readiness/barrows.json) | Priest in Peril completed; His Faithful Servants started. At least one enemy must be killed for chest loot. | Brother-style response; Prayer, consumable, inventory, travel, tunnel, and grave-recovery plan; named rune, equipment, diary, learning, or collection purpose. | Candidate when its variable runes or equipment meet a declared need and Morytania travel can share an episode with nearby work. | Stop at the named objective or when travel, supplies, or recovery cease to be acceptable. Re-enter for a new named purpose. | Prayer drain, tunnel state, chest rolls, and recovery are run-specific. The model lacks a canonical deterministic repeat-action outcome and comparative reward-value analysis. |
| Corrupted Gauntlet | `action:corrupted-gauntlet`; `pvm-readiness-core-activities`; [readiness package](../pvm-readiness/corrupted-gauntlet.json) | Song of the Elves completed and one normal Gauntlet completion explicitly observed. | In-instance preparation result; style, prayer-cycle, tornado, and floor-hazard plan; acceptable account-type risk; dedicated high-attention session; named learning, resource, equipment, or collection purpose. | Candidate when the account is intentionally ready for high-attention repeatable PvM and its potential rewards have a present purpose. External gear is not the gate. | Stop at the declared learning, attention, risk, resource, equipment, or collection boundary. Re-enter only after the formal unlock and a fresh high-attention objective are observed. | High repetition and failure risk. All completions and rewards are variable; Hardcore and Ultimate Ironman boundaries are explicit. No seed target, completion count, or readiness level is modeled. |

## Gear And Drop Bypasses

| Objective | Normalized records | Hard earliest access | Ideal-window candidate | Stop / re-entry | Random-drop and coverage boundary |
| --- | --- | --- | --- | --- | --- |
| Dragon defender | `action:fight-warriors-guild-cyclopes-for-dragon-defender`; `dragon-defender-warriors-guild`; `drop-bypass-readiness` | Warriors' Guild eligibility; basement access after the ordered bronze-through-rune chain and rune-defender hand-in; sufficient tokens or the documented exemption; melee against basement cyclopes. Equip requires 60 Defence. | Candidate when shield-slot offensive value has an immediate melee purpose and the account can support the staged chain. | Stop on observed ownership. Re-enter only while it remains unowned and the player still has an explicit combat purpose. | Every defender is RNG; token consumption depends on actual time. Numeric cyclops combat-stat coverage is still missing. An applicable death can require the modeled Perdu repair. |
| Zombie axe | `action:fight-armoured-zombies`; `action:repair-zombie-axe`; `zombie-axe-armoured-zombies`; `drop-bypass-readiness` | Defender of Varrock completion or the separately documented pre-completion instance state; an observed broken axe; 70 Smithing and an anvil to repair; 65 Attack to equip. | A conditional opportunity while doing armoured-zombie combat for another declared reason. Once observed and repaired, it supplies one-handed slash and crush capability. | Stop the acquisition window on broken-axe observation and evaluate repair; stop on completed-axe ownership. Re-enter only with an explicit purpose and neither form owned. | The broken axe is 1/800 in the verified package; it is not a default grind or a deterministic bypass. No deterministic alternative is modeled. |
| Warped sceptre | `action:fight-warped-creatures`; `warped-sceptre-warped-creatures`; `drop-bypass-readiness` | Partial Path of Glouphrie completion; 56 Slayer; crystal chime for tortoises; 62 Magic to wield after acquisition. | A conditional opportunity when powered-staff capability would solve a current combat need and eligible warped-creature combat already fits the account. | Stop on observed ownership. Re-enter only for a still-declared purpose while it remains unowned. | The sceptre is 1/320 in the verified package. Charges and casting supplies are separate requirements; no deterministic alternative, kill count, or setup is modeled. |
| Rune scimitar | `action:fight-zamorak-warriors-for-rune-scimitar`; `action:fight-fire-giants-for-rune-scimitar`; `rune-scimitar-drop-paths`; `drop-bypass-readiness` | 40 Attack to equip. Zamorak warriors require Ourania Cave access; fire giants require a chosen location's access. | Candidate only when a rune scimitar has present melee value and the kill source is already useful or convenient. | Stop on observed ownership. Re-enter only with an explicit purpose while still unowned. | Zamorak-warrior and fire-giant routes are RNG. The deterministic alternative is 90 Smithing plus two runite bars; neither drop route is baseline progression. Location-specific fire-giant access remains unmodeled. |
| Rune axe | `action:fight-enchanted-valley-tree-spirits`; `enchanted-valley-rune-axe-drop`; `drop-bypass-readiness` | Fairy-ring access, dramen or lunar staff unless exempt, Enchanted Valley travel, and an inventory axe to spawn a tree spirit. | A conditional side objective when the rune Woodcutting tier would immediately unlock useful gathering and Enchanted Valley access already serves another purpose. | Stop on observed ownership. Re-enter only for an explicit purpose while the axe remains unowned. | The axe is RNG. The deterministic alternative is Woodcutting Guild access and Perry's listed shop purchase; no kill count or combat setup is assumed. |

## Cross-Window Rules

- These objectives are active, high-attention content; none is an AFK or passive
  recommendation.
- A realized drop can remove or defer its conventional acquisition path. A
  possible drop does not reserve training, supplies, GP, or route position.
- Quest completion, a formal unlock, or a skill gate never proves survival,
  supplies, mechanics, reward value, or player interest.
- Bundle tags: `midgame-pvm`, `combat-gear`, `drop-bypass`; plus
  `varlamore` (Moons), `morytania` (Barrows), `prifddinas` (Corrupted
  Gauntlet), `asgarnia` (Royal Titans and Dragon defender), `varrock`
  (Zombie axe), `kandarin` (Warped sceptre), `ourania` or a selected
  fire-giant location (Rune scimitar), and `enchanted-valley` (Rune axe).
- Candidate comparison must use marginal current account value, nearby quest,
  diary, transport, and passive-reset work, then subtract detour, danger,
  supply pressure, repetition, and attention burden. It must not select by
  guide identity or a nominal level.

## Source And Confidence Boundary

This file reuses existing repository records only: `pvm-readiness-core-activities`,
`perilous-moons-readiness`, `drop-bypass-readiness`, the linked PvM readiness
packages, `strategy/pvm-readiness-contexts.json`,
`strategy/monster-drop-bypass-timing-contexts.json`, and
`strategy/project-philosophy.md`. Their cited Wiki, official, and community
sources establish mechanics; their readiness observations and this document's
ideal-window candidates are strategy, not factual eligibility or a route.

Missing coverage includes comparative reward valuation, travel time, kill time,
supply consumption, death cost, full inventory plans, exact gear sufficiency,
and player-specific mechanics performance. These must remain observations until
a selected episode justifies detailed validation.
