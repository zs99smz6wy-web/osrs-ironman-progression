# Convenience-Anchor Capacity Plan

## Purpose

This is the capacity checklist for developing the first playable merged opening
follow-up around the current default-anchor candidates:

- Daddy's Home completion;
- Gertrude's Cat completion if the relay is clean;
- Natural History Quiz;
- Children of the Sun;
- only low-friction handoffs needed to avoid real future blockers.

It is not player-facing route prose. It defines the proof required before a
research-only execution segment can be written and live-validated.

## Starting boundary to prove

The future segment must start from one exact bank checkpoint. The likely
candidate is a Varrock bank checkpoint after the first Varrock handoff loop, but
the segment must not assume that checkpoint until observed or constructed from a
validated prior segment.

Minimum start record:

| State | Required observation |
| --- | --- |
| Location | Exact bank or no-bank checkpoint. |
| Coins | Carried and banked coins separately if the route depends on a purchase. |
| Quest handoffs | Which of Rune Mysteries, Demon Slayer, Vampyre Slayer, Gertrude's Cat, Shield of Arrav, Priest in Peril, Daddy's Home, Romeo & Juliet, and Children of the Sun are started, progressed, or complete. |
| Banked bulky supplies | Logs, planks, cloth, nails, milk, sardine, doogle leaves, saw, hammer, bucket, pie dish, beer, and any quest scrolls. |
| Carried risk items | Any temporary drops, inventory-only keys, quest items, or food that would be painful to lose. |

## Anchor requirements

### Daddy's Home

| Requirement | Current known state | Capacity issue |
| --- | --- | --- |
| 10 regular planks | Required by fact record. | Ten inventory slots if carried together. |
| 5 bolts of cloth | Required by fact record. | Five inventory slots. |
| Nails | At least 16 successful nails; larger low-level reserve expected. | One stack, but exact reserve and nail type must be chosen. |
| Hammer | Required; source alternatives exist. | One slot unless already carried. |
| Saw | Required; source alternatives exist. | One slot unless supplied during miniquest at the right stage. |
| Waxwood logs/planks | Three obtained during miniquest. | Three slots during the relay; exact conversion handoff needs proof. |
| Crate rewards | Fixed crate output after completion. | Post-completion inventory may overflow without a bank plan. |

**Capacity implication:** carrying all Daddy's Home materials can consume at
least 18 non-stackable slots before waxwood and crate rewards. This anchor
almost certainly needs either a nearby bank break or an execution path that
stages materials in multiple trips.

### Gertrude's Cat

| Requirement | Current known state | Capacity issue |
| --- | --- | --- |
| 100 gp child payment | Listed in cash-deadline ledger. | Coin stack. |
| Milk | BRUHsailer step-14 loadout includes milk. | One slot unless obtained locally in the segment. |
| Raw sardine | BRUHsailer step-14 loadout includes sardine. | One slot unless obtained locally in the segment. |
| Doogle leaves | Both studies collect or preserve leaves. | One slot. |
| Kitten output | Completion can place a follower/pet state rather than ordinary inventory. | Needs player-observed follower/cat state, not inferred item state. |

**Capacity implication:** Gertrude's Cat adds modest slot pressure but competes
with Daddy's Home bulk. It may pair well only if the route banks between
purchase/material phases.

### Natural History Quiz

| Requirement | Current known state | Capacity issue |
| --- | --- | --- |
| Access | Varrock Museum basement. | No item slots recorded. |
| Output | 28 Kudos, 1,000 Hunter XP, 1,000 Slayer XP. | No inventory output. |

**Capacity implication:** this is capacity-light and attractive inside a
Varrock loop if the player is already nearby. Its main cost is time and route
attention, not items.

### Children of the Sun

| Requirement | Current known state | Capacity issue |
| --- | --- | --- |
| Access | First-Varrock guide loop in both source studies. | No major item pressure recorded in current opening studies. |
| Output | Completion and Varlamore access candidate. | Internal Quetzal network remains separate. |

**Capacity implication:** likely low slot burden, but its first real downstream
consumer remains untraced. It should not pull the route away from stronger
anchors unless it is naturally adjacent.

## Soft-handoff handling inside this segment

The future executable segment may include soft handoffs only when they satisfy
one of these conditions:

| Condition | Example |
| --- | --- |
| Free while already clicking the same NPC/location. | Starting a quest while passing the exact start NPC, with no extra carried item. |
| Prevents a confirmed near-term blocker. | Bucket/water/drain progress before a known Demon Slayer key consumer. |
| Does not crowd anchor materials. | Dialogue-only steps before withdrawing Daddy's Home supplies. |
| Has an easy skip/re-entry note. | A future optional Shield of Arrav faction branch. |

Soft handoffs should not be included merely because a source guide includes
them. They must fit the segment's bank and inventory budget.

## Macro-overlay skip rules to test

These are not omission decisions. They are the questions a capacity-aware
comparison must answer before the merged guide treats them as optional:

| Overlay | Safe-to-skip condition to prove |
| --- | --- |
| Rag and Bone Man I start | No unique bone-producing encounters occur before the next natural Varrock/east-of-Varrock return, or the guide accepts a future revisit. |
| Family Crest start | No brother-routing opportunity occurs before the next natural Dimintheis return, or the route does not value early goldsmithing-gauntlet progress yet. |
| Large log/arrowshaft work | No accepted Fletching, Wintertodt, ammunition, or quest-log target depends on the exact early quantity. |
| Broad BRUHsailer Varrock extras | Each deferred dialogue or pickup has a local replacement before its first named consumer. |
| Large food/wine reserves | The selected segment has no Stronghold, Wilderness, thieving, or dangerous combat leg needing that safety buffer. |

## Proposed proof workflow

1. Build a table of all required carried items for Daddy's Home alone.
2. Add Gertrude's Cat items and check whether one-trip execution still fits.
3. Add Natural History Quiz and Children of the Sun as low-slot inserts only if
   location routing is natural.
4. Add exactly one soft-handoff group at a time and reject it from the segment
   if it causes capacity or cognitive overload.
5. Record a bank checkpoint before any bulky purchase/build phase.
6. Record a bank checkpoint after Daddy's Home crate output.
7. Only after those checkpoints are coherent, write a research execution
   segment with concise instructions.

## Current working hypothesis

The first playable merged follow-up should probably use a banked,
two-phase pattern:

1. **Light Varrock phase:** capacity-light completions and dialogue handoffs,
   such as Natural History Quiz, Children of the Sun, and any free local starts
   that do not require bulky materials.
2. **Bulky construction/cat phase:** Daddy's Home materials, Gertrude's Cat
   supplies, completion checks, crate handling, and a final bank checkpoint.

This hypothesis is not a route decision. It exists because Daddy's Home's
material footprint is too large to hide inside a dense macroquesting paragraph
without risking the exact failure Dylan is trying to avoid: missing one item and
having the guide silently break.
