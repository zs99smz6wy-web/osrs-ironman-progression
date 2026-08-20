# Recommendation Contract

Future route output is a recommendation for a declared account state, never a generic ordered list emitted from raw facts.

## Required input

- Account state conforming to `data/schemas/account-state.schema.json`.
- A goal or set of allowed goals.
- Available attention window.
- Cash commitments with an explicit purpose and deadline.
- Whether the player accepts risk or high-intensity methods.

## Required output per major recommendation

- The proposed action and stop condition.
- Hard requirements currently satisfied and missing.
- Factual sources and graph relationships used.
- Strategic rationale, including why the timing is appropriate.
- Alternatives and bypasses, including any account-changing drops.
- Active and passive/AFK companion options suitable for the stated attention window.
- Re-entry condition: when it becomes worth returning after stopping.

## Prohibited output

- A bare skill target without an account purpose.
- An assumed rare drop as a mandatory requirement.
- A GP target without identified purchases.
- A claim that a method is AFK if it requires unattended or unsafe play.
- A collection-log recommendation whose reward has no stated account utility.
