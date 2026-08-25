# Milestone Skeleton

## Shape

This is a partially ordered milestone lattice, not a route. The account may move between lanes whenever current gates, reward value, geography, attention, or observed RNG make a different bundle stronger.

```text
                         fresh Ironman
                               |
              +----------------+----------------+
              |                |                |
        quest and XP       travel access    cash and supplies
              |                |                |
              +-------- permanent foundations -+
                               |
          +--------------------+--------------------+
          |                    |                    |
   passive systems       utility rewards       combat foundation
 birdhouses/seaweed     pouch/sacks/bags       levels/gear/practice
 contracts/tears              |                    |
          +-------------------+--------------------+
                              |
                    readiness-based content
          Titans / Moons / Barrows / later Gauntlet
                              |
                    new drops and unlocks feed
                    the next account snapshot
```

The connectors mean dependency or strategic reinforcement. They do not require every node in a row to be completed first.

## Milestone families

| Family | Route-shaping objectives | Enter when | Leave when |
| --- | --- | --- | --- |
| Opening dependency foundation | Shared Lumbridge quest starts, X Marks, first Varrock handoffs, Children of the Sun, Daddy's Home candidate | Several durable handoffs or unlocks can share the trip | Selected handoffs and one stable bank/resume point are complete |
| Early transport | Chronicle, spirit trees, gliders, Morytania, fairy rings, Fossil Island, POH, Varlamore, Sailing access | A network supports multiple near-term windows | The permanent access flag is secured; later extensions remain separate |
| Quest-XP thresholds | Waterfall, Gnome quests, Dig Site, Nature Spirit, Enter the Abyss, Temple of the Eye and other bounded fixed rewards | The quest's real blockers are met before wasteful manual training | The fixed reward and named unlock are claimed |
| Passive infrastructure | Birdhouses, giant seaweed, contracts, Tears, Kingdom | Setup supports a named supply or XP need without displacing a stronger purchase | Current cycle, funding boundary, or supply target is reached |
| Durable utility | Rune pouch, Herb sack, Seed box, Auto Weed, Coal bag, Gem bag, Fish Barrel opportunity, selected Mixology rewards | Current inventory, banking, spell, gathering, or potion friction justifies the reward | One named utility is owned; do not extend for unrelated completion |
| Combat capability | Useful quest XP, rune weapon paths, Dragon defender, Zombie axe or Warped sceptre opportunities | A current encounter or training objective needs the capability | The capability is observed or the attempt cost exceeds current value |
| Readiness PvM | Royal Titans, Perilous Moons, Barrows, Corrupted Gauntlet | Access, supplies, mechanics, recovery, attention, and reward purpose are all acceptable | Learning, reward, attention, risk, or session boundary is reached |
| Economic infrastructure | Deadline-backed GP, POH costs, Kingdom funding, Sailing checkpoints, Smithing pipelines | A named purchase or resource deadline exists | The deadline is funded or the chosen method stops serving another goal |

## Episode selection

For each decision horizon:

1. Evaluate factual eligibility from the current account state.
2. Classify each relevant objective into a content-window state.
3. Remove objectives without a named current or near-term benefit.
4. Form bundles from geography, quest handoffs, transport, diary, supply, and passive-reset overlap.
5. Compare marginal account value against danger, detour, repetition, supply pressure, and attention.
6. Keep alternatives when preference or account observations can change the result.
7. Validate the selected bundle against proven guide execution.
8. Only then acquire exact inventory, banking, shop, and step details for that episode.

## Opening decision horizon

The first comparison is not "B0aty or BRUHsailer." It asks which bounded post-Tutorial bundle best establishes:

- shared durable quest handoffs;
- useful first transport and regional access;
- enough cash and supplies for declared near-term purchases;
- an early XP threshold without unnecessary training;
- a stable bank/resume point;
- optional active and low-attention continuations.

B0aty and BRUHsailer supply proven bundle components and executable ordering. The project may retain, remove, move, or add components when the content windows and account goals explain the change.

## Implementation boundary

Do not add a global optimizer yet. The current scorer is a useful eligibility-ranked baseline, but its dimensions are mostly static. The next implementation should add only the minimum state-aware window classification needed to compare a small set of opening bundles. Detailed inventory modeling remains episode-scoped.
