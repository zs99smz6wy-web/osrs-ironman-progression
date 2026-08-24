# Rune Mysteries factual dossier

**Scope:** current Old School RuneScape factual reference for later central
integration. This is not a route, recommendation, or action-model change.

**Verification date:** 2026-08-24

## Formal quest facts

| Field | Current fact |
| --- | --- |
| Quest | Rune Mysteries |
| Membership | Free-to-play quest |
| Official difficulty / length | Novice / Short |
| Skill requirements | None |
| Quest requirements | None |
| Required starting items | None |
| Enemies required to defeat | None |
| Start NPC and location | Duke Horacio, on the first floor (UK; second floor US) of Lumbridge Castle |

The Wiki describes only optional fast travel to Varrock and, for members, to
the Wizards' Tower. Those are recommendations rather than formal quest
requirements. No coins, combat level, skill level, equipment, consumable, or
teleport is formally required.

## Quest-state checkpoints

These are the stable, strategically useful boundaries. `Partial progress`
means that the quest has begun but is not complete; it must never be treated as
a completed-quest prerequisite.

| State | Required interaction and resulting state | Item state after interaction | Location transition |
| --- | --- | --- | --- |
| Not started -> **quest started** | Speak to Duke Horacio and select `Have you any quests for me?`, then `Yes.` He asks the player to take a talisman to the head wizard. | Receive **1 air talisman**. Carry it to continue. | Lumbridge Castle -> Wizards' Tower. |
| **Partial progress: talisman delivered** | In the Wizards' Tower basement, speak to Archmage Sedridor and give him the air talisman. | Hand over **1 air talisman**; receive **1 research package**. Carry the package to continue. | Wizards' Tower basement -> Aubury's Rune Shop, Varrock. |
| **Partial progress: package delivered / notes obtained** | Speak to Aubury in the Varrock rune shop and choose `I've been sent here with a package for you.` while carrying the research package. He examines it and gives notes for Sedridor. | Hand over **1 research package**; receive **1 research notes**. Carry the notes to continue. | Varrock rune shop (south of Varrock east bank) -> Wizards' Tower basement. |
| **Quest complete** | Speak to Sedridor and give him the research notes. | Hand over **1 research notes**; receive/retain **1 air talisman** as the quest reward. | No further mandatory travel. |
| **Post-completion: Museum Kudos claimed** | After completion, speak to Historian Minas on the first floor (UK; second floor US) of Varrock Museum to claim the quest's Museum reward. | No quest item is required or consumed. | Any location -> Varrock Museum. This is a separate claim, not part of Rune Mysteries completion. |

The exact conversation can have extra narrative lines, but the item exchanges
above are the durable progression boundaries. The Wiki quick guide lists the
Sedridor, Aubury, and Sedridor sequence; Aubury's current transcript confirms
that the package is handed over and research notes are given in return.

## Item ledger and recovery behaviour

| Item | Quantity | How it enters the quest | Carried / handed off / consumed | Recovery or final disposition |
| --- | ---: | --- | --- | --- |
| Air talisman | 1 | Duke Horacio gives it when the quest starts. | Carry to Sedridor, then hand it over. | The quest rewards an air talisman on completion. If the starting talisman is lost before Sedridor, Duke Horacio can provide another. The completed reward talisman is a normal, tradeable air talisman. |
| Research package | 1 | Sedridor gives it after receiving the air talisman. | Carry to Aubury, then hand it over. | Untradeable, non-stackable quest item. It has a Destroy option; Sedridor supplies a replacement after loss/death. Requesting another while a copy is banked removes the banked copy. |
| Research notes | 1 | Aubury gives them after receiving the research package. | Carry to Sedridor, then hand them over to complete the quest. | Aubury can replace lost notes before the final handoff. |

No item is consumed by a skill action, and the quest has no GP cost. The three
quest-hand-off items are single-item exchanges; do not infer that possession of
an air talisman alone proves a particular quest stage because it is a normal
item with other sources and is also the completed quest reward.

## Locations, travel, dialogue, and risk boundaries

1. **Lumbridge Castle:** Duke Horacio is on the first floor (UK; second floor
   US). Start by asking for a quest and accepting it.
2. **Wizards' Tower:** travel south-west of Lumbridge to the tower; Sedridor is
   in the basement. Give him the air talisman and accept delivery of his
   research package to Aubury.
3. **Varrock:** Aubury is in the rune shop south of Varrock east bank. Deliver
   the package; he gives the research notes.
4. **Wizards' Tower basement:** return to Sedridor and give the notes to finish
   the quest.
5. **Varrock Museum, separately:** Historian Minas claims the 5 Kudos after
   completion. Completion itself neither awards the Kudos directly nor requires
   visiting the museum.

There are no enemies to defeat and no forced combat, puzzle, instance, item
spawn, or timed mechanic. The mandatory work is dialogue and travel between
ordinary world locations. This dossier deliberately does not classify an
overworld walking path as safe: normal world encounters, deaths, disconnects,
and player-selected transport remain outside the formal quest requirements.

## Deterministic completion rewards and unlocks

- 1 quest point.
- Ability to mine rune essence after asking an eligible wizard to teleport the
  player to the rune essence mine. At Mining level 30 or higher on members
  worlds, mined essence is pure essence; otherwise it is rune essence.
- 1 air talisman.
- Ability to apply random-event lamps and books of knowledge to Runecraft.
- 5 Museum Kudos, claimable separately from Historian Minas after completion.

The quest has no fixed skill-XP reward. It unlocks access related to Runecraft;
it does not itself grant Runecraft XP.

## RuneLite and Character Exporter observability

RuneLite can expose a quest's broad completion state, and the local Character
Exporter integration imports a quest only when its exported `quests.json`
state is exactly `FINISHED`. Therefore `Rune Mysteries = FINISHED` is a safe
completion observation.

The current project importer deliberately does **not** infer an in-progress
quest, a quest step, an item handoff, a Museum Kudos claim, or transport access
from Character Exporter data. In particular, the three partial checkpoints
above cannot be reconstructed safely from the phase-1 account state:

- non-`FINISHED` is not a precise stage identifier;
- inventory/bank presence of a research package or research notes is only a
  point-in-time observation, and both items have replacement behaviour;
- an air talisman is not stage-specific; and
- `Rune Mysteries` completion does not prove that the 5 Kudos have been claimed.

Later integration should model the start, two handoffs, completion, and Museum
claim as distinct player-confirmed observations unless a purpose-built RuneLite
quest-stage integration supplies a documented, stable stage signal.

## Sources

All URLs below were checked on 2026-08-24. The OSRS Wiki is the factual game
reference; the official OSRS site is listed only for its current official link
to that Wiki and did not provide a separate maintained Rune Mysteries
walkthrough during this check.

- [Rune Mysteries quick guide](https://oldschool.runescape.wiki/w/Rune_Mysteries/Quick_guide): formal requirements, start, NPC sequence, locations, no required enemies, rewards, and Kudos claim.
- [Research package](https://oldschool.runescape.wiki/w/Research_package): package properties and replacement/banked-copy behaviour.
- [Transcript: Aubury](https://oldschool.runescape.wiki/w/Transcript:Aubury): package handoff, research-notes receipt, and notes replacement dialogue.
- [Transcript: Duke Horacio](https://oldschool.runescape.wiki/w/Transcript:Duke_Horacio): replacement air-talisman dialogue before delivery to Sedridor.
- [Air talisman](https://oldschool.runescape.wiki/w/Air_talisman): ordinary item identity, altar use, and quest-reward source.
- [Runecraft](https://oldschool.runescape.wiki/w/Runecraft): post-quest rune/pure-essence mining access and Mining-level distinction.
- [Kudos](https://oldschool.runescape.wiki/w/Kudos): Rune Mysteries' separate 5-Kudos Museum claim.
- [Official Old School RuneScape site](https://oldschool.runescape.com/): current official site, which links to the OSRS Wiki.
- [Project account-ingestion boundary](../account-ingestion.md): current local RuneLite Character Exporter interpretation and its explicit in-progress-quest limitation.
