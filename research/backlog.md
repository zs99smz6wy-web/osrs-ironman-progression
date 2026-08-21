# Research Backlog

## Prioritized acquisition tranches

### 1. Kingdom and passive-resource closure

- Completed: verified and normalized `Throne of Miscellania` and `Royal Trouble` prerequisites, items, skills, rewards, fixed XP, and unlock relationships.
- Completed: verified coffer caps, daily withdrawal rules, worker counts, approval decay, and midnight processing without prescribing worker allocation or rush timing.
- Pending: design an observed Kingdom-status snapshot and parameterized coffer transfers; do not infer approval, daily deductions, or collection output from elapsed time.

### 2. Current Sailing access and utility closure

- Completed: revalidated `Pandemonium`, skiffs, bounty tasks, `Troubled Tortugans`, Great Conch/Gryphon access, Port Roberts, Wyrmscraig, and `Fallen From Grace` against current official and Wiki sources.
- Completed: verified Golem Crafting, Jeweller's Chisel, Shellbane Gryphon, and Belle's Folly facts, including their current random-drop rates and repair gate.
- Completed: normalized deterministic Sailing access, quest, and activity actions; represented random rewards with `makes_obtainable` edges rather than guaranteed state transitions.
- Pending: model Slayer-task and combat state before adding a Shellbane Gryphon action, then add Belle's Folly repair as a separate deterministic action. Keep preferred Sailing milestones and utility valuations in strategy.

### 3. Utility-minigame closure

- Completed: normalized `Enter the Abyss` and `Temple of the Eye` into Guardians of the Rift, reward searches, deterministic pearl purchases, and random unique-reward paths.
- Completed: normalized Tithe Farm and Auto-weed, `Sleeping Giants` and Giants' Foundry utility purchases, and Motherlode Mine reward milestones with spendable currencies separated from random acquisition.
- Completed: strengthened Tempoross and Fish Barrel modeling so permits support reward searches while the barrel remains `makes_obtainable`, never guaranteed.
- Pending: add strategic scores and account-specific stop conditions only after comparing these verified unlocks with alternative uses of their currencies and time.

## Continuing validation queue

- Quest XP, item, combat, and GP requirement records for early transport and Fossil Island chains.
- Birdhouse, farming, seaweed, and Tears passive-loop requirements and outputs.
- Perilous Moons and Belle's Folly: exact current hard gates, readiness thresholds, and reward utility.
- Giants' Foundry: reward costs, Smithing/GP/resource outputs, and natural stop candidates.
- Tempoross/Fish Barrel, Tithe Farm, Guardians of the Rift, and MTA: utility-first stop points.
- Rune axe and other low-cost monster-drop bypasses, including expected-time and combat-access analysis.
- Modern Sailing: economic inputs, repeatable-activity yields, Slayer-task state, combat readiness, and strategy-layer valuation of verified utility unlocks.

## Source mix

Use official Jagex announcements and game updates for release facts; OSRS Wiki pages for structured requirements and mechanics; established Ironman guides, GitHub projects, Reddit, and YouTube for strategies that are clearly labelled as community judgement. Any conflict should be recorded rather than silently resolved.
