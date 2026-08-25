# Smallest Practical Content-Window Evaluator Slice

## Decision

The first evaluator slice should classify a small set of already-normalized objectives for one declared account state. It should answer:

> Which objectives are factually possible, practically worth considering, or complete enough to stop, and what evidence is missing?

It should not select a route, assemble a global plan, predict training rates, or rank every action in the repository. The output is a bounded comparison input for opening-bundle research and later episode selection.

This slice is an adapter around the current evaluator and strategy contexts:

```text
account-state.example.json
        |
        v
validate_account_state()
        |
        v
evaluate_actions() --------------> factual eligibility and blockers
        |                                      |
        +------------------+-------------------+
                           v
                 window classification
                           |
                           v
              optional existing score/context
                           |
                           v
              comparison-ready objective rows
```

## Reuse points

The slice should consume existing contracts rather than introduce parallel ones.

| Existing component | Reuse in this slice | Boundary |
| --- | --- | --- |
| `scripts/evaluate_progression.py:validate_account_state` | Validate the complete account snapshot before classification. | Do not weaken the current required state shape or add fields. |
| `scripts/evaluate_progression.py:evaluate_actions` | Supply factual action status, missing hard requirements, preparation gaps, completion state, fact IDs, and normalized outputs. | Its `blocked`, `needs_preparation`, `eligible`, and `completed` statuses remain the factual source of truth. |
| `scripts/score_candidates.py:score_candidates` | Reuse only when an objective has an existing strategic annotation and is factually eligible. | Static candidate dimensions remain advisory; they do not become timing gates. |
| `strategy/content-window-contract.md` | Use the six window states, stop/re-entry boundary, and comparison rules. | No new top-level state vocabulary is needed. |
| Existing strategy analyzers | Attach already-supported transport, durable-utility, Sailing, combat-quest, and PvM context where an action has a matching context. | Context remains explanatory and must not silently change factual eligibility. |
| Content-window dossiers | Provide objective purpose, ideal-window candidates, delay cost, stop/re-entry language, risk, attention, and unresolved evidence. | Dossiers remain research inputs; they are not executable route instructions. |
| `strategy/candidates.json` | Provide bounded scoring annotations for the subset already covered. | Missing annotation means "unscored," not "bad candidate." |

## Exact inputs

The initial callable boundary should accept these existing documents and one small slice configuration. No new account fields are required.

### Required inputs

1. **Account state**: the existing `graph/account-state.example.json` shape, or a Runelite-derived state normalized into that shape.
   - Validate with `validate_account_state`.
   - Unknown observations stay unknown; missing evidence is not treated as zero, false, owned, or ready.

2. **Normalized actions document**: `data/progression/actions.json`.
   - Each selected objective must resolve to one action ID.
   - Requirements, preparation, completion, transitions, fact IDs, and action kind come from this document.

3. **Window catalog**: a small research-only mapping embedded in the eventual evaluator input or a future strategy JSON file. For this proposal, the catalog is the bounded action table below plus dossier references.
   - `action_id`
   - `window_id`
   - `purpose_required`: boolean
   - `purpose_note`
   - `ideal_triggers`: named observations or account facts already available
   - `delay_cost`: short bounded explanation
   - `stop_condition`
   - `reentry_condition`
   - `attention_class`: `active`, `semi_afk`, `low_attention`, or `true_afk`
   - `source_ids` and `confidence`

4. **Optional existing strategy documents**:
   - `strategy/candidates.json`
   - matching transport, utility, Sailing, combat-readiness, or PvM contexts

The slice must not accept a route, guide episode, inventory plan, bank plan, training method, or user-selected XP allocation as evaluator inputs.

## Exact output

Return one deterministic document with this shape. Field names are a proposal for the later implementation, not a request to edit production code in this tranche.

```json
{
  "schema_version": 1,
  "account_state_valid": true,
  "scope": "bounded content-window evaluation",
  "objectives": [
    {
      "window_id": "window:chronicle",
      "action_id": "action:buy-chronicle",
      "name": "Chronicle",
      "domain": "transport",
      "classification": "ready_candidate",
      "factual_action_status": "eligible",
      "missing_hard_requirements": [],
      "missing_preparation": [],
      "completion_evidence": [],
      "purpose_required": true,
      "purpose_status": "unconfirmed",
      "ideal_trigger_evidence": [],
      "stop_condition": "A charged Chronicle is observed, or the declared use is satisfied.",
      "reentry_condition": "A named teleport or replacement need appears.",
      "alternatives": [],
      "score_context": null,
      "source_ids": [],
      "unresolved": []
    }
  ],
  "summary": {
    "counts_by_classification": {},
    "eligible_unscored_action_ids": [],
    "validation_warnings": []
  }
}
```

The output must preserve the distinction between:

- `missing_hard_requirements`: factual blockers from the normalized action;
- `missing_preparation`: declared preparation conditions already represented by the action;
- `purpose_status`: strategy evidence about why the player might enter;
- `ideal_trigger_evidence`: observations that make timing especially attractive;
- `unresolved`: research or observation gaps that limit the claim.

Do not collapse those into one generic "missing" list. That would recreate the project problem of treating every absence as a quest or skill gate.

## Classification rules

Use the contract's six classifications with the following precedence. The precedence makes the result deterministic and prevents readiness advice from overriding factual eligibility.

1. **`stop_reached`**
   - The action completion condition is satisfied, or its named durable output/utility is confirmed in the account state.
   - For repeatable activities, use this only when the declared bounded objective has completion evidence. An eligible activity is not automatically stopped.

2. **`blocked`**
   - The factual action status is `blocked`.
   - Report the exact hard blockers returned by `evaluate_actions`.

3. **`accessible_not_ready`**
   - Factual status is `eligible` or `needs_preparation` after the action's hard gates are met, but a required declared purpose, readiness observation, supply boundary, attention boundary, or risk/recovery condition is unknown or unacceptable.
   - `needs_preparation` may remain visible as `factual_action_status`; the window classification explains the strategy-level reason.

4. **`ready_candidate`**
   - Factual status is `eligible`.
   - At least one named purpose or near-term account benefit is confirmed or explicitly declared.
   - No ideal trigger is strong enough to call it `ideal_candidate`.

5. **`ideal_candidate`**
   - The objective is `ready_candidate`, and at least one catalogued ideal trigger is currently evidenced: a useful threshold is available, a nearby handoff is confirmed, a reward has current account value, or delaying has a documented cost.
   - This is a timing signal, not a command to do the objective next.

6. **`reentry_candidate`**
   - The objective was previously stopped or completed for a bounded purpose, and a separate catalogued reward, threshold, utility, or account-state change now makes another visit useful.
   - The evaluator may emit this only when re-entry evidence is explicit. It must not infer re-entry from elapsed time alone.

If required purpose information is absent, classify an otherwise accessible objective as `accessible_not_ready`, with `purpose_status: "unconfirmed"`. This preserves the project rule that collection-log goals, skill targets, and GP targets need a named account benefit.

## Minimal bounded action set

The first implementation should cover only actions that already have both normalized factual representation and meaningful dossier guidance. This is enough to compare opening foundations without turning the evaluator into a global optimizer.

| Action ID | Window | Why included | Initial timing signal |
| --- | --- | --- | --- |
| `action:buy-chronicle` | `window:chronicle` | Small transport objective with explicit ownership/charge boundary. | Nearby Varrock work or a declared early transport purpose. |
| `action:children-of-the-sun` | `window:varlamore-entry` | Shared early regional access with a clear boundary at Varlamore entry. | A named Varlamore activity or first-Varrock handoff. |
| `action:tree-gnome-village` | `window:spirit-trees` | Permanent transport and fixed XP, already used by the scorer. | Transport network value or fixed combat-XP timing. |
| `action:grand-tree` | `window:gnome-gliders` | Gnome-glider access and fixed XP with real Agility gates. | Agility threshold and nearby Gnome/transport bundle. |
| `action:establish-player-owned-house` | `window:poh-foundation` | Durable account convenience with a bounded ownership stop. | A Varrock material relay or immediate house-use purpose. |
| `action:pandemonium` | `window:sailing-entry` | Sailing entry is separable from later shipbuilding and training. | A declared Sailing experience or Port Sarim opportunity. |
| `action:birdhouse-loop` | `window:passive-birdhouses` | Recurring passive system with explicit observation and recurrence semantics. | Fossil Island access plus a named Birdhouse supply/XP purpose. |
| `action:giant-seaweed-loop` | `window:passive-giant-seaweed` | Passive Crafting input system with bounded setup and repeat status. | Seaweed access and a future glass/Crafting purpose. |
| `action:buy-tithe-seed-box` | `window:seed-box` | Durable utility with fixed point cost and explicit demand boundary. | Current seed inventory pressure, not mere availability. |
| `action:buy-tithe-herb-sack` | `window:herb-sack` | Durable utility with competing Tithe/Slayer paths and Herblore use gate. | Observed grimy-herb pressure and a current currency choice. |
| `action:buy-coal-bag` | `window:coal-bag` | Durable utility whose value depends on a named Smithing pipeline. | Coal-heavy Smithing, Blast Furnace, or Foundry purpose. |
| `action:buy-gem-bag` | `window:gem-bag` | Durable inventory convenience with a bounded purchase objective. | Repeated gem/mining/Crafting inventory pressure. |
| `action:buy-mta-rune-pouch` | `window:rune-pouch` | Utility with a high attention cost and explicit alternative paths. | Three-rune storage has immediate value and MTA is acceptable. |
| `action:tempoross` | `window:fish-barrel` | Reward opportunity must remain separate from a guaranteed transition. | Fishing/food purpose; Fish Barrel remains an observed opportunity. |
| `action:enter-mastering-mixology-session` | `window:mixology` | Correctly needs Herblore, input reserve, and named reward purpose. | Eligible input stock and selected durable utility; never Herb sack. |
| `action:barrows` | `window:barrows` | PvM content with existing readiness observations and reward-purpose boundary. | Access, supplies, recovery, tactics, and named objective observed. |
| `action:moons-of-peril` | `window:perilous-moons` | Current project priority and existing internal-supply observations. | Quest/access plus combat and recovery evidence. |
| `action:corrupted-gauntlet` | `window:corrupted-gauntlet` | High-attention PvM must not be inferred from formal access alone. | Formal access plus explicit preparation, tactic, and risk evidence. |

The bounded IDs above resolve against `data/progression/actions.json`. The evaluator should reject an unknown ID rather than silently substitute a similarly named action.

The first slice should not include every diary task, every quest-XP action, every monster-drop bypass, or every opening-guide step. Those remain valuable data, but they need either a purpose/threshold adapter or episode-specific detail before they can produce useful timing classifications.

## Validation rules

The slice should validate its own catalog and output without changing production validators.

### Input validation

- Every catalog action ID resolves exactly once in `actions.json`.
- Every action has one stable window ID and one dossier or strategy source reference.
- Every referenced fact, context, and source ID exists where the repository already provides a canonical lookup; unresolved external research is listed explicitly rather than fabricated.
- `attention_class` uses only the four existing attention values.
- `ideal_triggers`, stop conditions, and re-entry conditions are non-empty and concise.
- A repeatable action must not declare `stop_reached` from mere action eligibility.
- Candidate annotations may be absent; absence produces an unscored result, not an error.
- No catalog field may add or override action requirements, transitions, resource counts, XP, or reward ownership.

### Classification validation

- `blocked` requires at least one factual blocker.
- `accessible_not_ready` requires a readiness, purpose, observation, or preparation explanation.
- `ready_candidate` and `ideal_candidate` require factual `eligible` status.
- `ideal_candidate` requires at least one explicit trigger evidence item.
- `stop_reached` requires completion or named-output evidence.
- `reentry_candidate` requires explicit prior-stop/completion evidence plus a current re-entry trigger.
- Unknown observations cannot satisfy an ideal trigger.
- The evaluator must never allocate XP, infer a training method, infer a drop, treat an unobserved item as owned, or turn a strategy preference into a hard blocker.
- Every output row includes `fact_ids`, source IDs, unresolved gaps, and the factual action status for auditability.

### Regression cases

The eventual focused tests should cover only this slice first:

- fresh account: shared opening actions classify as blocked or accessible with purpose unconfirmed;
- post-Tutorial state: Chronicle, Children of the Sun, and other no/low-gate actions retain their factual status without becoming automatic recommendations;
- missing supplies: action remains blocked or needs preparation with the exact missing input;
- utility owned: the bounded purchase classifies as `stop_reached` and does not suggest another copy;
- eligible utility without demand: `accessible_not_ready`, not `ideal_candidate`;
- observed nearby handoff: the same eligible action becomes `ideal_candidate`;
- PvM access without combat observations: `accessible_not_ready`;
- completed one-time action versus eligible repeatable activity: distinct stop behavior;
- unknown Fish Barrel, unique drop, or collection-log observation never becomes owned or complete;
- a candidate with no `strategy/candidates.json` annotation appears as eligible but unscored.

## What this enables

Once this slice exists, opening-bundle comparison can consume a small table of classified objectives:

```text
classified objectives
        |
        +--> discard factual blockers
        +--> retain accessible objectives with stated gaps
        +--> prefer ideal candidates only when evidence supports it
        +--> group by existing geography/handoff tags
        +--> apply existing static score as context
        +--> keep alternatives when purpose or observation is unknown
```

That is enough to compare a lean shared opening, a cash/transport opening, a broad regional opening, and a state-triggered hybrid. It also tells us where detailed inventory research is justified. It does not attempt to decide the complete account route.

## Explicit non-goals

- No global optimizer, search tree, or exhaustive bundle enumeration.
- No new account-state schema fields.
- No route order, guide prose, inventory list, bank relay, or RuneLite step generation.
- No automatic quest-XP allocation or training recommendation.
- No predicted drop rates, activity rates, GP rates, or future supplies.
- No claim that B0aty or BRUHsailer is globally optimal.
- No replacement of `evaluate_actions` or `score_candidates`.
- No production-code edits are required by this research slice; implementation should begin only after this boundary is accepted.

## Acceptance boundary

The slice is ready for implementation when one evaluator test can take the existing example account state plus the bounded catalog and produce deterministic rows that:

1. preserve factual action statuses and exact blockers;
2. distinguish access from readiness and ideal timing;
3. report stop and re-entry only from explicit evidence;
4. expose unscored but eligible actions;
5. attach existing strategy context without changing eligibility; and
6. leave route selection and detailed episode validation to the next layer.
