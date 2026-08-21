# Research Backlog

## Prioritized acquisition tranches

### 1. Kingdom and passive-resource closure

- Completed: verified and normalized `Throne of Miscellania` and `Royal Trouble` prerequisites, items, skills, rewards, fixed XP, and unlock relationships.
- Completed: verified coffer caps, daily withdrawal rules, worker counts, approval decay, and midnight processing without prescribing worker allocation or rush timing.
- Completed: added an optional, player-observed Kingdom snapshot for approval, worker assignments, collection-pause status, and observation time, plus exact parameterized coffer deposits and withdrawals with quest-appropriate caps. Neither path infers wages, approval decay, resource output, or elapsed time.

### 2. Current Sailing access and utility closure

- Completed: revalidated `Pandemonium`, skiffs, bounty tasks, `Troubled Tortugans`, Great Conch/Gryphon access, Port Roberts, Wyrmscraig, and `Fallen From Grace` against current official and Wiki sources.
- Completed: verified Golem Crafting, Jeweller's Chisel, Shellbane Gryphon, and Belle's Folly facts, including their current random-drop rates and repair gate.
- Completed: normalized deterministic Sailing access, quest, and activity actions; represented random rewards with `makes_obtainable` edges rather than guaranteed state transitions.
- Completed: added explicit observed Slayer-task state, a task-gated Shellbane Gryphon action that never invents kills or drops, and a separate deterministic Belle's Folly repair action.
- Pending: model account-specific combat readiness and keep preferred Sailing milestones and utility valuations in strategy.

### 3. Utility-minigame closure

- Completed: normalized `Enter the Abyss` and `Temple of the Eye` into Guardians of the Rift, reward searches, deterministic pearl purchases, and random unique-reward paths.
- Completed: normalized Tithe Farm and Auto-weed, `Sleeping Giants` and Giants' Foundry utility purchases, and Motherlode Mine reward milestones with spendable currencies separated from random acquisition.
- Completed: strengthened Tempoross and Fish Barrel modeling so permits support reward searches while the barrel remains `makes_obtainable`, never guaranteed.
- Pending: add strategic scores and account-specific stop conditions only after comparing these verified unlocks with alternative uses of their currencies and time.

### 4. Economic bottleneck and monster-drop bypass closure

- Completed: verified the hard gates, fixed payouts, variable outputs, attention notes, and guide-estimate boundaries for Agility Pyramid, wealthy-citizen valuables, Giants' Foundry commissions, silk stalls, blackjacking, Sailing bounties, shipwreck salvaging, and Port Roberts stalls.
- Completed: normalized concrete cash commitments and added a deadline-aware account-state analyzer that reports funding shortfalls without choosing a money-making method or route.
- Completed: verified and graphed Rune axe, Zombie axe, Warped sceptre, Rune scimitar, and Dragon defender acquisition paths; random drops use `makes_obtainable`, while purchases, smithing, and repairs remain deterministic.
- Completed: added transparent expected-kill and cumulative-drop probability inputs plus sourced encounter facts for the selected bypasses without inventing kills per hour or declaring account readiness.
- Pending: supply an actual account combat snapshot and measured or sourced encounter throughput before estimating time, then score the verified economic methods and bypasses in the strategy layer.

## Continuing validation queue

- Quest XP, item, combat, and GP requirement records for early transport and Fossil Island chains.
- Completed: revalidated birdhouse, giant-seaweed, farming-contract, and Tears passive-loop requirements, reusable and consumed inputs, offline waiting, active interaction, recurrence gates, and fixed-versus-variable outputs.
- Completed: added observed recurring-system readiness separately from permanent loop flags; timestamps are preserved but never advance timers, grant outputs, or infer completion.
- Completed: normalized player-confirmed birdhouse, giant-seaweed, Tears, and Kingdom collection/reset actions; explicit ready observations are consumed, while timers and variable rewards remain uninferred.
- Completed: verified and normalized Perilous Moons hard quest and skill gates, fixed quest XP, encounter mechanics, internal supplies, Lunar Chest reward behavior, duplicate protection, and Moon-set utility/degradation. Community readiness recommendations remain labelled as judgement rather than requirements.
- Perilous Moons: evaluate account-specific combat readiness and strategic stop conditions without converting community recommendations into hard gates.
- Giants' Foundry: reward costs, Smithing/GP/resource outputs, and natural stop candidates.
- Tempoross/Fish Barrel, Tithe Farm, Guardians of the Rift, and MTA: utility-first stop points.
- Monster-drop bypass measured throughput and account-specific combat-readiness analysis using the now-verified encounter and probability inputs.
- Modern Sailing: economic inputs, repeatable-activity yields, Slayer-task state, combat readiness, and strategy-layer valuation of verified utility unlocks.

## Source mix

Use official Jagex announcements and game updates for release facts; OSRS Wiki pages for structured requirements and mechanics; established Ironman guides, GitHub projects, Reddit, and YouTube for strategies that are clearly labelled as community judgement. Any conflict should be recorded rather than silently resolved.
