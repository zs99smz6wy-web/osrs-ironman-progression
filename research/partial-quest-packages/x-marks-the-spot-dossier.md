# X Marks the Spot: factual dossier

## Record metadata

- Quest: X Marks the Spot, quest #142.
- Verification date: 2026-08-24.
- Scope: current factual requirements, quest-state checkpoints, item transitions, locations, rewards, and observation boundaries.
- This dossier records game facts only. It does not select an order for this quest relative to other content or make a strategic recommendation.

## Formal requirements and identity

- Members status: Free-to-play.
- Quest series: Great Kourend, #1.
- Official difficulty: Novice.
- Official length: Very Short.
- Start NPC and location: Veos in The Sheared Ram pub in Lumbridge.
- Formal requirements: none. There are no quest, skill, membership, combat, or GP requirements listed for starting or completing the quest.
- Required item: one functional spade. The Eastfloor spade does not work for this quest.
- Enemies to defeat: none.
- Visiting Great Kourend is not required to complete the quest. The dialogue can differ if the player has already visited Great Kourend.
- Completion relationship: X Marks the Spot is a requirement for Client of Kourend. Unlocking Kourend is listed as auto-completing X Marks the Spot.

## Item accounting

The quest uses one current quest object at a time. The clue objects are received as the quest advances and are not extra preparation requirements.

| Item | Quantity | State or transaction | Consumed, retained, or conditional |
| --- | ---: | --- | --- |
| Functional spade | 1 | Carried for each of the four dig interactions | Used as a tool; not consumed. The Eastfloor spade is not a valid substitute. |
| Treasure scroll, first clue | 1 | Veos gives it after the player offers to help | Current quest object until the first dig. |
| Treasure scroll, second clue | 1 | Received after the first correct dig | Current quest object until the second dig. |
| Mysterious orb | 1 | Received after the second correct dig | Current quest object for locating the third clue; not a required preparation item. |
| Treasure scroll, fourth clue | 1 | Received after the third correct dig | Current quest object until the fourth dig. |
| Ancient casket | 1 | Received after the fourth correct dig | Carried to Veos and handed over to complete the quest. |
| Coins | 200 | Quest reward at completion | Received; no quest GP payment is required. |
| Antique lamp (X Marks the Spot) | 1 | Quest reward at completion | Non-bankable; grants 300 experience in a skill chosen when used. It can be reclaimed from Veos if lost or destroyed. Item ID 23072. |
| Beginner scroll box | 0 or 1 | Completion reward only when the player does not already have one in their possession | Conditional reward. The current quest page says it can be claimed later if the player had one in their possession. |

No food, armour, weapon, runes, teleport item, energy potion, stamina potion, or other consumable is a formal quest requirement. Energy or stamina potions and one fast trip to Draynor Village using an amulet of glory are listed as recommendations, not requirements.

## Stable quest-state checkpoints

The following checkpoints describe the observable quest progression without treating travel or dialogue alone as completion of a later stage.

### Checkpoint 0: not started

- Quest is not complete and no X Marks the Spot quest object has been received.
- No formal preparation item is required beyond the spade needed before the first dig.

### Checkpoint 1: quest started; first clue held

- Interaction: speak with Veos in The Sheared Ram in Lumbridge and offer to help with the treasure hunt.
- Result: receive one treasure scroll containing the first clue.
- First clue text: “Within the town of Lumbridge lives a man named Bob. He walks out of his door and takes 1 step east, 7 steps north, 5 steps west and 1 step south. Once he arrives, he digs a hole and buries his treasure.”
- Veos can provide hints at The Sheared Ram in Lumbridge or at the Port Sarim dock location.

### Checkpoint 2: first clue resolved; second clue held

- Travel landmark: Bob's Brilliant Axes in Lumbridge.
- Dig location: the tile north of the north-western window of the house connected to Bob's Brilliant Axes, directly west of the plant.
- Interaction: dig the correct tile with one functional spade.
- Result: receive the next treasure scroll, the second clue.

### Checkpoint 3: second clue resolved; mysterious orb held

- Travel landmark: the door behind Lumbridge Castle by the Cook's kitchen.
- Dig location: the tile directly south-west of the large crate.
- Interaction: dig the map location with one functional spade.
- Result: receive one mysterious orb.

### Checkpoint 4: third clue resolved; fourth clue held

- Item interaction: feel the mysterious orb to compare its temperature while moving between locations. The orb reports relative distance to the hidden location; the quest page describes the distance as the number of steps ignoring obstacles, using Chebyshev distance.
- Travel landmarks: east of Draynor Village, north-west of the jail, south of the wheat field, near Leela.
- Dig location: four tiles north of the bush near Leela.
- Interaction: dig the correct tile with one functional spade.
- Result: receive the next treasure scroll, the fourth clue.
- Nearby hazard noted by the source: jail guards can be aggressive to lower-level players. This is a location fact, not a quest combat requirement.

### Checkpoint 5: fourth clue resolved; ancient casket held

- Clue type: Caesar-shift cipher.
- Cipher text: `ESBZOPS QJH QFO`.
- Decoded location: `DRAYNOR PIG PEN`.
- Travel landmark: pig pen just north of the Draynor Village market.
- Dig location: the centre of the pig pen.
- Interaction: dig the correct tile with one functional spade.
- Result: receive one ancient casket. The source records a faint whisper when it is unearthed.

### Checkpoint 6: quest complete

- Travel landmark: the northernmost dock in Port Sarim, outside the Rusty Anchor Inn.
- Interaction: give the ancient casket to Veos.
- Completion result: X Marks the Spot becomes complete and the completion rewards are issued.
- The casket is the object handed to Veos; the quest page does not list any additional item required for this final interaction.

## Travel-location inventory

The quest's named locations and landmarks are:

1. The Sheared Ram, Lumbridge: Veos start and hint location.
2. Bob's Brilliant Axes, Lumbridge: first clue landmark and first dig area.
3. Lumbridge Castle, behind the castle by the Cook's kitchen: second clue map and second dig area.
4. East of Draynor Village, north-west of the jail, south of the wheat field, near Leela: mysterious-orb target and third dig area.
5. Draynor Village market pig pen: fourth clue and final dig area.
6. Northernmost Port Sarim dock outside the Rusty Anchor Inn: Veos completion location and hint location.

The quest does not require a particular transport method. An amulet of glory is documented only as an optional fast trip to Draynor Village.

## Deterministic rewards and choice boundary

On completion, the current quest page lists:

- 1 quest point.
- 200 coins.
- 1 Antique lamp (X Marks the Spot), granting 300 experience in a skill chosen by the player.
- Ability to receive scroll boxes in place of clue scrolls, subject to the applicable scroll-box rules and caps.
- 1 beginner scroll box if the player does not already have one in their possession; the page states that it can be claimed later if the player had one in their possession.
- A +1 cap on all tiers of clue scrolls.

The lamp choice boundary is factual: the current reward description permits the player to choose the skill receiving the 300 experience, and the skill table records the choice as unrestricted by a quest skill requirement. The dossier does not assign a preferred skill. The lamp cannot be banked and may be reclaimed from Veos after being destroyed or lost.

The current reward is a beginner scroll box, not the older beginner scroll wording. The OSRS Wiki records the change on 9 July 2025, following the 2 July 2025 scroll-box update.

## RuneLite and Character Exporter observability limits

These limits describe the current project integration boundary, not a claim that the game has no internal variables for the quest.

- Quest completion can be represented as a finished quest after a RuneLite or Character Exporter observation. The current project treats quest completion as a reliable coarse observation when the relevant quest state is explicitly present.
- The raw Character Exporter v0.6.0 quest dataset supports `NOT_STARTED`, `IN_PROGRESS`, and `FINISHED` rows. The current importer normalizes only `FINISHED` quest names into `quests_completed`; it does not preserve an X Marks the Spot `IN_PROGRESS` stage as durable account state.
- A future or local RuneLite adapter may see the current inventory and identify a spade, treasure scroll, mysterious orb, ancient casket, lamp, or scroll box by item ID when that container is exported or observable. Item presence alone does not prove which dig occurred, which clue text was solved, the exact NPC interaction, or the causal relationship between an item and this quest.
- The current bridge has no exact event contract for the four dig coordinates, the orb's temperature readings, Caesar-shift decoding, the map clue, the casket hand-in, or the moment a quest object is replaced. These remain player-observed or manually confirmed substeps.
- A quest row marked `IN_PROGRESS` plus a quest-object item can suggest partial progress, but the current normalized model must not infer a precise stage from that combination.
- A finished quest row can support the coarse completion state, but a Character Exporter snapshot does not by itself attribute the 200 coins, lamp, beginner scroll box, or clue-cap change to a particular interaction. Inventory, bank, and skill-XP snapshots can show resulting state when present; they do not provide an event history or prove the lamp's selected skill.
- Travel, bank visits, time spent, clue attempts, incorrect digs, orb readings, and the player's safety experience are not reconstructed from the current export contract.

## Sources

All sources below were checked on 2026-08-24.

- [OSRS Wiki: X Marks the Spot](https://oldschool.runescape.wiki/w/X_Marks_the_Spot) - current quest metadata, requirements, locations, clue stages, completion interaction, rewards, and 2025 reward changes.
- [OSRS Wiki: Antique lamp (X Marks the Spot)](https://oldschool.runescape.wiki/w/Antique_lamp_%28X_Marks_the_Spot%29) - lamp item behavior, 300 XP amount, non-bankable status, reclaim behavior, and item ID 23072.
- [OSRS Wiki: Item IDs](https://oldschool.runescape.wiki/w/Item_IDs) - current numeric item identity reference, including Ancient casket 23071 and Antique lamp (X Marks the Spot) 23072.
- [Old School RuneScape: Old School Content Poll #63](https://oldschool.runescape.com/polls/2019/1541) - official Jagex poll record for adding X Marks the Spot as a short F2P quest with no requirements and its Great Kourend/mainland link.
- [OSRS Wiki: Beginner clue scroll](https://oldschool.runescape.wiki/w/Treasure_Trails/Full_guide/Beginner) - current beginner clue/scroll-box terminology and the post-completion scroll-box context.
