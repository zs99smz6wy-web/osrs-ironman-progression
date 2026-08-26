# Research-Only Execution Segments

Execution segments are short, sourced itinerary fragments below the canonical normalized action layer. They preserve practical checkpoints such as where an interaction occurs, whether a bank interaction is required, exact carried and banked requirements, optional alternatives, and explicit player observations.

Rendered instructions follow [Guide Writing Style](guide-writing-style.md): imperative first, one action per step, usually 3-12 words. Detailed rationale and source boundaries stay outside the main instruction.

They are research artifacts, not route output. A segment cannot select itself, apply a normalized action, acquire an item or GP, declare a result, estimate time without a cited range, or treat a player plan as completion.

Each segment also has a purpose section. It can explain the bounded utility of the fragment and the currently observed account facts that make it relevant to inspect. Its applicability and timing observation are explicitly not route selection, ranking, or an instruction to leave the player's present activity.

## Coverage Status

- `normalized_action`: The step links to an existing canonical action ID. It remains a reference only and must have a corresponding coarse-action boundary.
- `sourced_unmodeled_substep`: The fact and its source support the smaller instruction, but the canonical model has no action/state field for it.
- `unresolved`: The checkpoint is intentionally kept outside the current model until a factual source and a separate normalization review exist.

Partial quest state is especially important. A quest start, stage, or player-provided external progress observation cannot be represented as a completed quest merely because a completion node or action exists elsewhere. The proof segment demonstrates this with an unresolved Rune Mysteries start/partial checkpoint and an optional, separately observed Rune Mysteries Museum claim.

## Safety And Passive Checks

`safety_hcim` separates sourced hazard facts from player risk acceptance and current observations. An absent hazard record does not prove a safe trip, survival, escape, or return; all of those remain player observations. This makes the same evidence usable by an Ironman or HCIM without silently treating a route fragment as risk-approved.

A passive or recurring check records its trigger, the current observation required before acting on it, and an interruption policy. It may notice an opportunity, but cannot compel timer-chasing. In particular, a timer that may be ready is not a reason to abandon an active quest, Slayer task, encounter, or other player-committed activity.

## Package Layout

- Contract: `research/package-schemas/execution-segment.schema.json`
- Validator: `scripts/validate_execution_segments.py`
- Template: `research/execution-segments/template.json`
- Manifest: `research/execution-segments/integration-manifest.json`
- Proof: `research/execution-segments/post-tutorial-varrock-museum-proof.json`
- Interface prototype: `research/execution-segments/lumbridge-first-relay.json`
- Opening merge basis: `research/opening-guides/opening-action-union.json`

Run `python scripts/validate_execution_segments.py` to validate the package. The validator cross-checks linked normalized action IDs, local source references, ordered mainline steps, exact requirement quantities, coverage boundaries, and the prohibition on modeling a partial quest checkpoint as a normalized action.
