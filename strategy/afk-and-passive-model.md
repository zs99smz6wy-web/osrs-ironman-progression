# AFK and Passive Model

The route model has two lanes: an active objective and a parallel passive or low-attention lane.

## Attention labels

- `true_afk`: infrequent interaction while the player remains present and safe.
- `low_attention`: regular but light interaction.
- `semi_afk`: requires periodic decisions or repositioning.
- `active`: sustained input or risk management.

No recommendation should assume unattended overnight play or accept avoidable death risk as AFK.

Factual AFK or low-attention method research belongs in `research/afk-method-packages/` and uses `research/package-schemas/afk-method-package.schema.json`. That contract records mechanics, evidence cadence, safety, outputs, and proposed normalization only; timing, utility, and account-specific recommendations remain strategy-layer work.

## Recurring systems

Model farming, birdhouses, giant seaweed, Managing Miscellania, Tears of Guthix, and contracts as one of:

- `always`: worth integrating whenever unlocked and stocked.
- `usually`: worthwhile when travel and supplies align.
- `situational`: useful only for a stated resource or skill target.

Every AFK recommendation needs a duration window, inventory or bank preparation, expected outputs, stop condition, interaction frequency, and death-risk label.

## State boundaries

Keep three layers separate:

- `passive_loops` records whether the account has established permanent access to a recurring system.
- `recurring_observations` records a player-observed state such as `needs_inputs`, `in_progress`, `ready`, `cooldown`, or `unknown`, together with when it was observed and any explicitly recorded ready time.
- `kingdom_observation` records an optional player-confirmed Kingdom snapshot: approval, worker assignments, collection-pause status, and when those values were observed. It is valid only after the Kingdom loop is established and does not calculate daily deductions, approval decay, resource output, or elapsed time.
- Collection or reset actions apply only player-confirmed outcomes. A passed timestamp never grants experience, items, currency, or completion by itself.

An absent observation means the current readiness is unknown. It must not be treated as ready, blocked, or completed.
