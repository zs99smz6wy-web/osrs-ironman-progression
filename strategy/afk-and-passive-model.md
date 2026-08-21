# AFK and Passive Model

The route model has two lanes: an active objective and a parallel passive or low-attention lane.

## Attention labels

- `true_afk`: infrequent interaction while the player remains present and safe.
- `low_attention`: regular but light interaction.
- `semi_afk`: requires periodic decisions or repositioning.
- `active`: sustained input or risk management.

No recommendation should assume unattended overnight play or accept avoidable death risk as AFK.

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
- Collection or reset actions apply only player-confirmed outcomes. A passed timestamp never grants experience, items, currency, or completion by itself.

An absent observation means the current readiness is unknown. It must not be treated as ready, blocked, or completed.
