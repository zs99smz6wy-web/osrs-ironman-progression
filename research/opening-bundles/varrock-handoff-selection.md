# First-Varrock Handoff Selection

Research decision record for the provisional baseline. It selects only durable
quest states or bounded completion targets that are worth carrying across a
bank break. It does not choose an order, create a production action, or make a
partial quest state machine authoritative.

## Decision

Promote exactly two first-Varrock items into the provisional baseline:

1. **Rune Mysteries: Aubury accepted the research package.** This is the one
   promoted *partial* state. Both openings create it, it has a concrete return
   handoff at Sedridor, and its current package gives an explicit
   player-confirmation boundary.
2. **Daddy's Home: completion as a bounded follow-up target.** This is not a
   promoted partial state. Completion establishes the existing
   `daddys_home_completed` / `poh_owned` path, which aligns with the default
   profile's highest permanent-utility priority. Its inputs, fixed rewards,
   variable-nail boundary, and fresh-account transition are now normalized.

Children of the Sun completion remains in the provisional baseline through its
existing normalized action. It is a completed regional-unlock action, not a
new Varrock handoff to promote here. X Marks the Spot, The Restless Ghost, and
the earlier Rune Mysteries handoffs remain governed by their existing
research-only packages; they are outside this first-Varrock selection except
where they provide a prerequisite or return-trip reason.

## Selection Criteria

A state is promoted only when all of the following hold:

- it survives a bank break without relying on an ordinary carried item;
- it has a named, near-term downstream use under the default objective profile;
- its exact resume condition is observable by completion import or explicit
  player confirmation;
- it is supported by both opening studies, unless a stronger existing
  normalized content-window decision already justifies it; and
- it does not force social coordination, combat, a coin commitment, or an
  unbounded detour before the associated content window is active.

This applies the profile's preference for permanent utility, timely access,
and quest-XP timing while retaining its rules against unplanned cash work,
risk without a named benefit, and inferring unobserved state.

## Compared States

| Quest and candidate state | Downstream value | Opening-study support | Observability and exact durable resume condition | Decision |
| --- | --- | --- | --- | --- |
| **Rune Mysteries: package delivered to Aubury** | Places the account one return visit from Rune Mysteries completion, rune-essence-mine access, later Enter the Abyss / Temple of the Eye / Guardians paths, and a separate 5-Kudos claim. Completion timing can remain aligned with a Wizards' Tower return. | **Both.** Each delivers the package to Aubury during first Varrock work and delays completion. | **Player confirmation required:** Aubury accepted the research package and supplied research notes. Resume only when the player confirms that handoff; notes in inventory alone do not prove it, and the package documents replacement behavior. The next durable return condition is delivery of research notes to Sedridor and quest-list completion. | **Promote now.** The existing partial package already defines this stable, non-completion boundary. |
| **Daddy's Home: completed** | Establishes the free initial-house alternative, avoiding the 1,000-coin purchase and enabling the separately modeled `poh_owned` foundation. This matches the default profile's high permanent-convenience value without implying later POH rooms, relocation, or teleports. | **Both.** Both start it in first Varrock work and finish on the immediate Varrock follow-up. | **Completion observation required:** miniquest completion plus the resulting `daddys_home_completed` / `poh_owned` milestone. Saw, waxwood logs/planks, furniture-removal progress, and the crate are not durable partial-state proof. | **Promote now as a bounded completion target; do not promote an interim checkpoint.** The normalized action exposes exact fixed materials and rewards while reporting variable bent nails and the pre-existing-house coin branch. |
| **Demon Slayer: Sir Prysin's three-key request, then externally sourced keys** | Starts a later Silverlight/Delrith combat chain, Shadow of the Storm and Defender of Varrock dependencies, and a separate 5-Kudos claim after completion. It has no fixed XP and no current baseline content window. | **Both.** Both start and advance it in first Varrock; both defer completion substantially. | **Player confirmation required:** Sir Prysin made the three-key request. Individual keys and Silverlight are useful execution handoffs but are carried-item states, not durable account proof. Resume for keys/bones/Silverlight only when the later combat or prerequisite window is active. | **Defer.** Useful multiquest work, but not a persistent baseline state before a named Silverlight, combat, or Defender of Varrock purpose. |
| **Vampyre Slayer: Dr Harlow gave the stake** | Preserves a low-cost later Count Draynor completion, 4,825 Attack XP, and the direct Sins of the Father prerequisite. | **Both.** Each starts it in Draynor and has a Varrock Dr Harlow handoff; both defer completion. | **Player confirmation required:** Dr Harlow accepted beer and gave the stake. Garlic and the stake are inventory evidence only and must not be inferred from RuneLite export. Resume when Count Draynor combat readiness or the Morytania/Vampyre chain is active. | **Defer.** The fixed XP is real, but combat and a named threshold or chain purpose should choose its timing. |
| **Gertrude's Cat: playground location disclosed or kitten obtained** | Completion supplies a kitten and unlocks Icthlarin's Little Helper, Evil Dave, and later cat/diary branches; it also gives fixed Cooking XP. | **Both start/progress; completion is BRUHsailer-only in the reviewed B0aty trace.** | **Player confirmation required:** Shilop/Wilough disclosed the playground location, or the quest kitten was obtained. A generic cat observation cannot prove the quest follower state; completion is the durable condition. | **Research.** It may be a good geography bundle with Daddy's Home, but there is not yet consensus completion evidence or an active downstream cat window. |
| **Shield of Arrav: faction selected and own half secured** | Leads to Heroes' Quest, Defender of Varrock, and a separate 5-Kudos claim with a level-20+ lamp after completion. | **Both start it.** Both deliberately preserve flexible completion; BRUHsailer explicitly keeps a faction/partner branch open. | **Player confirmation required:** faction selected. Own shield half and certificate exchange are useful social handoffs, but neither proves partner availability. Resume only with an explicitly confirmed, trustworthy opposite-faction partner and a real downstream deadline. | **Defer.** The default profile rejects brittle external dependencies without a usable fallback. No baseline faction choice. |
| **Priest in Peril: quest started** | Completion unlocks Morytania, Nature Spirit, Ghosts Ahoy, Barrows access, Morytania transport, and 1,406 Prayer XP. It is a major later regional and fairy-ring-chain dependency. | **Both start it in first Varrock and defer completion.** | Starting is player-confirmable but has no durable functional effect. The first useful partial condition is **Drezel requests 50 unnoted essence**, which is not reached in either first-Varrock opening. Resume completion only when a Morytania objective is active and the bucket, 50 essence, combat plan, inventory trips, and risk plan are ready. | **Defer.** Preserve the option in execution notes, but do not model a bare start as baseline account state. |
| **Romeo & Juliet: Apothecary requests cadava berries** | Completion is a later Making Friends with My Arm and Defender of Varrock prerequisite and gives 5 Quest Points, but no skill XP or durable item. | **BRUHsailer-only** in the reviewed first-Varrock arc. | **Player confirmation required:** Apothecary requested cadava berries. This is the sole useful external-procurement handoff; other partial dialogue states are journal-only. | **Defer.** No shared opening evidence or active downstream deadline. |

## Shared Dependency Boundary

The following facts constrain this selection without creating more promoted
states:

- **Children of the Sun** is a shared, already normalized completion. Its
  Varlamore access supports later content, but it does not grant the internal
  Quetzal network.
- **The Restless Ghost** and **Priest in Peril** jointly gate Nature Spirit,
  Ghosts Ahoy, and the eventual fairy-ring path. Both opening studies support
  starting or progressing them before completion; neither creates an opening
  deadline for their completions.
- **Rune Mysteries completion** is required for Enter the Abyss, then Temple of
  the Eye and Guardians of the Rift. The promoted Aubury handoff preserves that
  option without claiming those later activities are ready.
- **Shield of Arrav, Demon Slayer, and Romeo & Juliet** later converge on
  Defender of Varrock, but its 55 Smithing and 52 Hunter gates, prerequisite
  chain, and combat boundary make that convergence a research fact, not a
  reason to force their starts or completions now.

## Consequence for Episode Design

The provisional first-Varrock episode may carry the Rune Mysteries Aubury
handoff and target Daddy's Home completion. It may record the other quest
starts as execution-local convenience only after their selected episode has
an independent reason to visit the relevant NPCs. No current guide state,
account import, or evaluator output may infer any of those starts from items,
quest rewards, or proximity.

Before any promotion becomes production data, separately review the checkpoint
schema, source-linked facts, RuneLite observability, account transition, and
the exact inventory/bank relay for the chosen episode.
