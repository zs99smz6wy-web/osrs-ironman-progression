# Content Window Contract

## Purpose

A content window describes when an objective becomes possible, useful, and no longer worth extending. It is strategy attached to sourced facts, not a fixed route position.

The project optimizes useful access, reward timing, variety, and sustainable progress. It does not optimize total level, a 99, or route compression without a named account benefit.

## Window states

| State | Meaning |
| --- | --- |
| `blocked` | A factual quest, skill, item, coin, transport, or account gate is missing. |
| `accessible_not_ready` | Hard gates are met, but declared combat, supply, risk, attention, or reward-purpose conditions are not. |
| `ready_candidate` | The account can reasonably enter for a named purpose. |
| `ideal_candidate` | Current rewards, nearby work, XP thresholds, or unlock value make this a particularly strong time to enter. |
| `stop_reached` | The named utility reward, unlock, bounded XP threshold, or session objective is complete. |
| `reentry_candidate` | A later reward, threshold, account state, or content dependency makes returning useful. |

## Required record

Each content-window record must contain:

- stable `id`, objective name, domain, and current status;
- normalized action and fact IDs already available;
- hard earliest-access gates, with missing coverage named;
- readiness conditions that remain strategy or player observation;
- one or more ideal-window candidates and why they matter;
- delay costs and reasons to enter later instead;
- a bounded stop condition and explicit re-entry condition;
- permanent rewards, downstream unlocks, and competing alternatives;
- geography and bundle tags used to form multi-output episodes;
- risk, attention, repetition, and AFK/passive compatibility;
- source and confidence boundary;
- unresolved data that prevents stronger timing claims.

## Rules

- Hard gates come only from factual records or cited current sources.
- Readiness recommendations never become hidden eligibility gates.
- Random drops create opportunities and stop checks, not guaranteed transitions.
- A collection-log objective needs a named utility, enjoyment, or completion goal.
- A skill target needs a named unlock, reward, quest-XP threshold, or supply purpose.
- A GP target needs identified purchases and deadlines.
- A route may enter content more than once when separate rewards have different ideal windows.
- Proven guides are execution and sequencing evidence. Agreement is a strong baseline, not proof of optimality.
- Detailed inventory validation begins only after a window is selected for an episode.

## Comparison rule

Candidate bundles are compared by marginal account value, not by guide identity:

1. eliminate bundles blocked by factual dependencies;
2. identify rewards whose value is currently high or decays if delayed;
3. add geographic, quest-handoff, diary, transport, and passive-reset synergy;
4. subtract detour, danger, supply pressure, repetition, and attention burden;
5. retain alternatives when scores depend on player preference or unobserved state;
6. use proven guides to validate the selected bundle's executable ordering.

The result is a recommendation for a declared state, not a universal total order.
