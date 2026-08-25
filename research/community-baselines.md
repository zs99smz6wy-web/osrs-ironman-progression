# Community Baselines

Community guides are strategy sources. Established routes such as BRUHsailer and B0aty are also field-tested implementations that players have followed and their authors have iterated when steps fail or create friction. That gives their sequencing strong empirical weight. They do not establish mechanics, requirements, drop rates, or current costs without a primary or structured factual source, and deviations still need explicit justification against their different goals and assumptions.

## BRUHsailer

BRUHsailer is the current macro-efficiency comparison baseline. The current public site was reviewed on 2026-08-24 and says it was last updated 2026-08-16. Its web implementation is useful for discovering dependencies, geographic bundles, and established route conventions.

Reusable patterns from the guide:

- chapter and numbered-step organization that turns a long route into resumable episodes;
- elapsed-time labels, GP-stack checkpoints, item-needed lists, and explicit preparation gates;
- optional activities, alternative methods, and stop/continue notes embedded beside the main action;
- macro sequencing that combines travel, questing, skilling, banking, and passive timers into one episode.

These are presentation and research patterns for this project, not facts to import into the route. BRUHsailer makes universal assumptions, favors HCIM and highly sweaty macro-efficiency routing, uses fixed lamp allocations, and often relies on assumed RNG, output, or throughput. Those assumptions are too coarse for an enjoyable, account-aware guide that must observe the player's inventory, attention budget, preferences, readiness, and actual drops before choosing the next episode.

## B0aty HCIM Guide V3

B0aty's HCIM Guide V3 was reviewed on 2026-08-24; the Wiki page reports a last modification date of 2026-08-18. It is strictly community strategy evidence. Its useful reusable patterns are bank-to-bank episodes with concrete inventories, macroquesting that bundles nearby objectives, passive farm and birdhouse triggers that run alongside active play, explicit safety notes, alternatives when a preferred method is unavailable or undesirable, and milestone-based timing for unlocking later content.

The guide is especially useful for showing how a progression plan can remain actionable without describing every individual tick. Its limits are equally important: it is HCIM-oriented, can prefer risk-averse or sweaty routing, may assume fixed lamp choices and expected RNG/output, and its milestone ordering is not automatically correct for a normal Ironman or for this project's enjoyment-first account model. We should borrow the episode grammar and trigger discipline, then re-evaluate each action against observed account state, content enjoyment, safety tolerance, alternatives, and permanent reward value.

This project diverges deliberately when its objective differs: a recommendation must remain account-state-aware, explain its timing, support varied play, and offer credible alternatives where an optimal high-intensity method creates disproportionate burnout risk.

## The blackjacking case

Recent r/ironscape threads describe the familiar 50-to-77 Thieving or early-million-GP blackjacking block as highly efficient but often unpleasant enough to cause players to abandon a route. Those threads also mention Wealthy Varlamorians, stealing valuables, artefacts, and Port Roberts as alternatives. This is preference evidence, not a factual performance claim.

The model response is not "blackjacking bad". It is: identify the actual upcoming purchases, compare acquisition paths by their total account outputs and attention cost, and let the account state and user tolerance choose the method.

## Relevant implementation references

Iron Hub shows useful interaction patterns for this project: tracking actual account state, exposing QoL unlocks, modelling POH progression, and giving collection-log information without making collection-log completion the sole objective. Its implementation must not be copied blindly; it is an interface and systems-design reference.

## Source identifiers

- `bruhsailer-web`
- `community-bruhsailer-current`
- `community-b0aty-hcim-guide-v3`
- `reddit-blackjacking-alternatives-2026`
- `reddit-latest-guide-2026`
- `github-iron-hub`
- `youtube-varlamore-ironman-guide`
