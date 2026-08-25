# Port Sarim Pandemonium Opening Bundle

Status: bounded research contract; not route prose.

Scope: define the evidence needed to evaluate `action:pandemonium` as a
component of the provisional opening baseline. This package does not select an
ordering, prescribe player steps, or expand Pandemonium into a general Sailing
training plan.

## Decision Boundary

The current evidence supports Pandemonium as a strong Port Sarim candidate
when the selected opening already reaches Port Sarim and the player wants
Sailing access or additional early content variety. It does not support
assuming that Pandemonium should be completed on every fresh account, that a
Skiff should be funded immediately, or that Sailing training follows in the
same episode.

The relevant production action is `action:pandemonium`. The relevant factual
record is `sailing-entry-pandemonium`. The timing window is
`window:sailing-entry`, whose stop boundary is Sailing access and Pandemonium's
fixed rewards.

## Bundle Contract

### Start location

The bundle must record:

- **Required start area:** Port Sarim.
- **Start interaction:** speak with Will or Anne at Port Sarim.
- **Area precision still needed:** the exact start NPC/tile and the account's
  pre-quest resume point must be captured during episode validation.

The current facts establish Port Sarim as the quest-start location. They do
not establish a prior bank, a particular arrival method, a safe corridor, or a
specific inventory layout.

### End location

The bundle must record the observed post-completion location and the nearest
usable bank or resume point. This is intentionally episode evidence rather
than a production assumption. The current Pandemonium fact/action records
define completion and rewards, but do not define a post-quest tile, banking
interaction, or automatic return transport.

At minimum, the episode record should distinguish:

1. quest completion confirmed;
2. Sailing access confirmed;
3. rewards confirmed;
4. player location after the final interaction;
5. bank or next-bundle handoff available, if any.

### Hard inputs

The normalized model currently records:

- membership;
- the ability to start at Port Sarim;
- no quest requirement;
- no skill requirement;
- no imported item requirement;
- no coin requirement.

The action therefore has empty modeled `requirements` and empty
`preparation`. This is a statement about the current factual model, not proof
that every temporary quest interaction is inventory-free. Episode validation
must record any temporary tools, consumables, combat supplies, dialogue
requirements, or account-state gates encountered in the live game before they
are promoted into production data.

Do not add Skiff materials, shipbuilding supplies, a 15,000-coin purchase, or
Sailing levels to Pandemonium's hard inputs. Those belong to later, separately
modeled Sailing checkpoints.

### Fixed outputs

On completion, the current factual/action model supports these fixed outputs:

- Pandemonium completed;
- Sailing access milestone;
- 300 Sailing XP;
- one Raft;
- one Captain's log;
- 25 sawmill coupons.

The bundle may use Sailing access as its strategic output. It must not treat
the following as Pandemonium outputs:

- Skiff ownership;
- Port Piscarilius access;
- shipbuilding progress;
- Sailing bounty access;
- salvage access;
- any later destination or transport network;
- a guaranteed coin or resource rate from Sailing.

Those are separate content windows and remain subject to their own gates.

### Inventory effects

The production transition currently models the following additions:

| State | Effect | Evidence status |
| --- | --- | --- |
| Items | Ensure at least one `sailing_raft` | Fixed modeled output |
| Items | Ensure at least one `captains_log` | Fixed modeled output |
| Items | Add 25 `sawmill_coupon` | Fixed modeled output |
| Skill XP | Add 300 Sailing XP | Fixed modeled output |

No input consumption is currently modeled. Episode evidence must still capture
the actual inventory before and after completion, including whether the raft or
Captain's log arrives in inventory, whether coupons are stackable in the
observed interface, and whether any temporary quest items remain or disappear.
This is needed for slot planning and does not authorize changing the action
until the evidence is reviewed.

The action uses `ensure_min` for the two unique items. That preserves the
account-state model's conservative behavior when a snapshot already contains
one, but the episode ledger should distinguish a newly awarded item from an
already-owned item.

## Bank And Resume Contract

The bundle needs a before/after state pair, not a full reconstruction of every
guide inventory.

### Before Pandemonium

Record only the inputs relevant to this episode:

- current location;
- coins;
- free inventory slots;
- quest state for Pandemonium;
- any observed temporary item or supply requirement;
- the selected neighboring Port Sarim objectives;
- whether a bank relay is needed before starting.

### After Pandemonium

Record:

- completion and Sailing access flags;
- Sailing XP delta;
- raft, Captain's log, and sawmill coupon deltas;
- free inventory slots after rewards;
- current location;
- whether a bank visit is needed before the next selected objective;
- whether the next objective is a Port Sarim handoff, a travel action, or a
  later Sailing checkpoint.

The evidence package should prove one stable resume state, such as a banked
Port Sarim or nearby handoff state, without declaring that state to be the
universal route endpoint. Exact withdrawal order, slot arrangement, and
teleport choices remain episode-level until an episode is selected for guide
writing.

## Compatible Provisional-Baseline Work

The following work is compatible in principle with a Port Sarim Pandemonium
bundle because it already belongs to the current opening horizon or shares a
Port Sarim handoff. Compatibility is not a required ordering.

| Candidate | Why it fits | Boundary |
| --- | --- | --- |
| X Marks the Spot completion | Its fixed completion interaction is at the northern Port Sarim dock outside the Rusty Anchor Inn. | Preserve the separate spade/input and choice-XP boundaries; do not merge its reward transition with Pandemonium. |
| Port Sarim travel and Veos observation | The opening ledger already treats Port Sarim as a transport and Kourend handoff area. | Record the selected destination and fare/state only when used; do not infer that Pandemonium grants transport. |
| Entrana ferry or deposit-box interaction | It is a nearby Port Sarim candidate with a real equipment restriction. | Keep the deposit box distinct from a full-bank checkpoint and validate the inventory restriction separately. |
| Children of the Sun / first-Varrock work | Both are provisional-baseline content components with current-access value. | They are separate regional/quest actions; retain their own requirements, locations, and stop conditions. |
| Natural History Quiz | It is a provisional first-Varrock candidate with fixed XP and Kudos. | Do not use Pandemonium as evidence for Museum eligibility or vice versa. |

The episode may include several of these only after the selected bundle has a
declared purpose for each. Shared geography alone is insufficient.

## What Must Remain Episode-Level

Keep the following out of the general Pandemonium action and opening-bundle
fact model until a later, explicitly scoped episode is chosen:

- exact NPC dialogue and movement sequence;
- exact Port Sarim arrival path;
- exact bank withdrawals, deposits, and inventory slot order;
- temporary quest items and consumables not yet normalized;
- combat method, food, prayer, or gear assumptions;
- exact post-completion tile and logout/resume position;
- whether to continue into Sailing immediately;
- Sailing XP training method or target level;
- Skiff timing, 15,000-coin funding, and ship materials;
- bounty tasks, salvaging, shipbuilding, destinations, or later Sailing quests;
- optional transport purchases such as Chronicle;
- claims that the bundle is faster, safer, or universally optimal;
- any guide-specific step copied from B0aty or BRUHsailer without current
  mechanic validation.

The two proven opening guides are useful for testing whether a Port Sarim
handoff and multi-objective relay is executable. Their ordering and inventory
choices remain strategic evidence, not hard requirements.

## Minimum Evidence To Promote The Bundle

Promote Pandemonium from candidate component to an executable opening episode
only when the following bounded evidence exists:

1. Current quest-start and completion locations are confirmed.
2. No additional hard skill, quest, item, coin, combat, or temporary-input gate
   has been found, or each newly found gate is documented separately.
3. Fixed rewards match the factual record.
4. Inventory deltas and slot impact are observed.
5. A before/after bank or resume state is recorded.
6. At least one compatible neighboring objective has a named purpose and a
   separate completion boundary.
7. The episode states whether it stops at Sailing access or intentionally
   enters a later Sailing window.

Until then, Pandemonium remains a bounded Port Sarim candidate in the
provisional baseline, not a finalized guide segment.

## Local Evidence

- `data/facts/sailing-core.json`: `sailing-entry-pandemonium` and later Sailing
  checkpoints.
- `data/progression/actions.json`: `action:pandemonium` and
  `action:buy-sailing-skiff`.
- `strategy/content-window-catalog.json`: `window:sailing-entry`.
- `research/content-windows/quest-unlocks-and-xp.md`: Sailing timing window.
- `research/content-windows/evaluator-slice.md`: evaluator boundary for
  Pandemonium.
- `research/opening-ledger/travel-safety.md`: Port Sarim, Veos, and Entrana
  transport boundaries.
- `research/opening-ledger/supply-economy.md`: early cash and inventory
  constraints.
- `research/opening-guides/fresh-start-comparison.md`: proven-opening
  comparison and evidence weighting.
- `research/opening-bundles/default-profile-evaluation.md`: provisional
  baseline and remaining Pandemonium handoff gap.
