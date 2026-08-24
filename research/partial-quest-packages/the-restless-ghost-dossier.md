# The Restless Ghost: factual dossier

- Game: Old School RuneScape
- Quest: The Restless Ghost (#3)
- Members: No
- Official difficulty: Novice
- Official length: Short
- Quest series: None
- Verification date: 2026-08-24
- Scope: current factual quest data and observation limits only. This document does not select a route order or make a strategic recommendation.

## Formal requirements

The current OSRS Wiki quest page lists:

- No skill requirement.
- No prerequisite quest.
- No formal item requirement.
- Encounter capability: the player must be able to kill or run from a combat level 13 skeleton. Killing it is not required.

The quest is free-to-play. It begins by speaking to Father Aereck in the Lumbridge church/chapel south-east of Lumbridge Castle, near Bob's Brilliant Axes.

## Stable quest checkpoints

These are externally meaningful checkpoints. They are deliberately named rather than represented as unverified Jagex quest-variable or varbit numbers.

### 1. Quest accepted from Father Aereck

- Interaction: speak to Father Aereck and accept the quest.
- Result: The Restless Ghost becomes in progress. Father Aereck identifies the haunted graveyard and directs the player to Father Urhney in a small house in the far west of Lumbridge Swamp.
- Item delta: none.
- Inventory or GP requirement: none, apart from normal space for any unrelated carried items.

### 2. Ghostspeak amulet received from Father Urhney

- Location: Father Urhney's house in Lumbridge Swamp.
- Interaction: tell Father Urhney that Father Aereck sent the player about the ghost.
- Result: Father Urhney gives one Ghostspeak amulet.
- Capacity: at least one free inventory slot is required to receive the amulet.
- Item delta: `Ghostspeak amulet x1` received; no item is consumed.
- Operational requirement: the amulet must be worn to understand the Restless ghost's quest dialogue. The amulet can be carried or equipped for travel between checkpoints.
- This is a partial quest checkpoint, not quest completion.

### 3. Restless ghost contacted and skull request established

- Location: Lumbridge Graveyard, in the small building containing the marble coffin south of the church, in the graveyard's south-east area.
- Travel input: return from Father Urhney's house to the Lumbridge graveyard. Running is sufficient; no teleport is required.
- Interaction: wear the Ghostspeak amulet, open/search the coffin, and speak to the ghost.
- Result: the ghost explains that a warlock took his skull and directs the player toward the Wizards' Tower south of Draynor Village. The corpse is headless. This is the quest-progress condition that enables the skull retrieval.
- Item delta: none.
- Carried items: Ghostspeak amulet equipped for the conversation; no other quest item is required.

### 4. Ghost's skull retrieved from the altar

- Location: Wizards' Tower, on the island south of Draynor Village; enter the tower and descend to the basement. The quest altar is in the basement.
- Travel input: travel from Lumbridge to the Wizards' Tower by the normal surface route. A teleport is optional, not a formal requirement.
- Interaction: search the altar after the ghost has identified the missing skull.
- Result: one Ghost's skull is obtained. A level 13 quest Skeleton animates and attacks when the skull is taken.
- Capacity: at least one free inventory slot is required to take the skull.
- Item delta: `Ghost's skull x1` received; it is a temporary quest item.
- The Skeleton does not have to be killed. Leaving the room or tower with the skull is a valid completion path for this checkpoint.

### 5. Coffin completion and quest completion

- Location: return to the same marble coffin in the Lumbridge Graveyard.
- Interaction: use `Ghost's skull x1` on the coffin. The ghost's spirit flies into the River Lum.
- Result: The Restless Ghost is completed and the coffin changes to its completed state, with the skull returned to it. The temporary Ghost's skull is no longer a player-carried item after the interaction.
- Item delta: `Ghost's skull x1` removed from the player's carried items and placed in the coffin; the Ghostspeak amulet remains available.
- Completion output: the quest-completion rewards below are applied.

## Locations and travel facts

The factual visit sequence is:

`Lumbridge church / Father Aereck -> Father Urhney's house in Lumbridge Swamp -> Lumbridge Graveyard coffin -> Wizards' Tower basement altar -> Lumbridge Graveyard coffin`

Location facts:

- Father Aereck is in the Lumbridge church/chapel east or south-east of Lumbridge Castle.
- Father Urhney lives in a small house in the western part of Lumbridge Swamp.
- The Restless ghost's coffin is south of the Lumbridge church, within the graveyard, in a small building in the south-east part of the graveyard.
- The Wizards' Tower is on an island south of Draynor Village. The relevant altar is in its basement.
- No quest-specific transport item, fee, or teleport is required.
- The quest page lists three Lumbridge teleports as a recommendation and a necklace of passage as a members-only recommendation for teleporting to the Wizards' Tower. These are optional travel aids, not formal requirements.

## Item, quantity, and GP accounting

| Item or resource | Quantity | State | Fact |
| --- | ---: | --- | --- |
| Formal quest items before starting | 0 | required | The quest page lists `None` for items required. |
| Coins / GP | 0 | required | No quest payment is listed or needed. |
| Ghostspeak amulet | 1 | received at checkpoint 2; retained | Given by Father Urhney. It is not consumed by talking to the ghost or by quest completion. |
| Ghost's skull | 1 | received at checkpoint 4; consumed as a player-carried quest item at checkpoint 5 | Taken from the Wizards' Tower basement altar and returned to the coffin. |
| Food, weapon, armour, runes, tools, and teleport items | 0 | formal requirement | None is listed. Any such supplies are player-selected and are not quest inputs in the formal data. |

The only capacity gates created by the quest interactions are the need for an open inventory slot when receiving the amulet and when taking the skull. The quest does not require a bank visit.

## Enemy and risk facts

- The quest Skeleton is combat level 13 and appears at the Wizards' Tower basement altar when the Ghost's skull is taken.
- The Skeleton can be avoided by running away after taking the skull; killing it is not required for the quest.
- The quest page states that this Skeleton does not count toward a Skeleton Slayer task and does not give the normal amount of combat experience when fought.
- The Skeleton's existence is the only enemy encounter listed as a formal completion capability for this quest.
- Father Aereck's starting dialogue warns that the Lumbridge Swamp may be dangerous. No additional combat gate is listed by the quest page.
- The coffin automatically closes after three minutes once opened, according to the coffin object page. This is an interaction-state fact, not a quest timer or a required elapsed-time condition.

## Deterministic XP, rewards, and unlocks

On completion the quest gives:

- 1 quest point.
- 1,125 Prayer experience.
- The Ghostspeak amulet as the persistent quest item associated with the quest; it is actually received earlier from Father Urhney and remains available after completion.

The OSRS Wiki records an edge case in which completing the quest with 0 prior Prayer experience raises Prayer from level 1 to level 9. This is a source-reported reward exception and is separate from the standard numeric reward of 1,125 Prayer XP.

Completion is listed as a prerequisite for:

- Animal Magnetism
- Cabin Fever
- Curse of the Empty Lord
- Creature of Fenkenstrain
- Ghosts Ahoy
- Making History
- Nature Spirit

The Ghostspeak amulet's deterministic capability is speaking to ghosts. It is used by later ghost-related quests and content; possessing the amulet is distinct from the quest-completion flag.

## Ghostspeak amulet persistence and replacement

- The amulet is untradeable and is retained after The Restless Ghost.
- It is not a charged item for this quest and no quest interaction consumes it.
- If the player loses it, Father Urhney is the documented replacement source, including after quest completion.
- Father Urhney will not issue a replacement when the amulet is still found in the player's inventory, equipment, or bank; the item must actually be lost from the locations checked by the game.
- A replacement is a new copy of the same persistent utility item, not a new quest-completion reward and not evidence that the quest was restarted.

## RuneLite and Character Exporter observability limits

The current repository's Character Exporter import contract supports finished quest names and, when present and resolvable, inventory, equipment, and bank containers. The following boundaries apply to this quest:

- A raw RuneLite Character Export quest row can carry `NOT_STARTED`, `IN_PROGRESS`, or `FINISHED`, but the current phase-1 importer adds only `FINISHED` quests to `quests_completed`.
- The importer does not normalize or preserve the exact partial stage: quest accepted, amulet received, ghost conversation completed, skull taken, or coffin opened with the skull.
- `quests_completed` can establish the final quest-completion flag after a fresh export. It cannot establish which NPC conversation, travel leg, or reward interaction produced it.
- An amulet or skull observed in an exported inventory, equipment, or bank can establish physical presence when the relevant dataset and item resolver support it. Presence alone cannot prove the player's exact Restless Ghost stage, whether the item came from this quest, or whether the skull is currently eligible for the coffin interaction.
- A missing amulet in an export does not by itself prove that it was lost: the export may omit a container, the item may be in an unsupported storage location, or the snapshot may be stale.
- The phase-1 import does not observe travel, NPC dialogue, coffin/altar interactions, Skeleton aggro, running away, combat success, the Prayer XP provenance, or the precise moment the skull is consumed.
- A future RuneLite guide surface can display the quest as complete from the quest state and can suggest manual confirmation from item observations, but partial quest checkpoints and the coffin transition require player confirmation unless a dedicated, tested client event contract is added.

## Sources

All sources below were checked for this dossier on 2026-08-24.

1. OSRS Wiki, [The Restless Ghost](https://oldschool.runescape.wiki/w/The_Restless_Ghost) - quest identity, formal requirements, locations, walkthrough, Skeleton encounter, XP, quest point, amulet, and completion prerequisites.
2. OSRS Wiki, [Transcript: Father Aereck](https://oldschool.runescape.wiki/w/Transcript:Father_Aereck) - quest-start dialogue, Father Urhney destination, and swamp warning.
3. OSRS Wiki, [Transcript: Restless ghost](https://oldschool.runescape.wiki/w/Transcript:Restless_ghost) - amulet-gated dialogue, missing-skull state, post-skull state, and coffin completion dialogue.
4. OSRS Wiki, [Altar (The Restless Ghost)](https://oldschool.runescape.wiki/w/Altar_(The_Restless_Ghost)) - Wizards' Tower basement altar, progression gate, skull retrieval, and altar state.
5. OSRS Wiki, [Coffin (The Restless Ghost)](https://oldschool.runescape.wiki/w/Coffin_(The_Restless_Ghost)) - coffin location, open/complete states, skull return, object ID, and automatic closing behavior.
6. OSRS Wiki, [Skeleton (The Restless Ghost)](https://oldschool.runescape.wiki/w/Skeleton_%28The_Restless_Ghost%29) - level 13 enemy, avoidable encounter, Slayer-task behavior, and combat-XP note.
7. OSRS Wiki, [Father Urhney](https://oldschool.runescape.wiki/w/Father_Urhney) - amulet source, location, and replacement behavior.
8. Official Old School RuneScape, [Old School Content Poll #70](https://oldschool.runescape.com/polls/2020/1602) - official poll record confirming the level 13 Restless Ghost Skeleton was not lowered by the proposed change.
