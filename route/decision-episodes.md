# Explicit Decision Episodes

`scripts/run_decision_episode.py` records a short, player-directed sequence of already completed actions. It is an audit tool, not a route generator: it composes recommendation options before every requested step but never chooses an action for the player.

The second positional argument is a JSON array of at most 25 ordered step objects. Each step requires an action ID and must explicitly confirm that the player completed it. An optional `option_id` records a player choice when the canonical action transition has multiple viable options.

```json
[
  {
    "action_id": "action:tree-gnome-village",
    "completion_confirmed": true
  },
  {
    "action_id": "action:the-dig-site",
    "completion_confirmed": true,
    "option_id": "uncut-opal"
  }
]
```

Run it with an account-state file and that selection file:

```text
python scripts/run_decision_episode.py path/to/account-state.json path/to/episode.json
```

For every requested step, the report stores the recommendation chapter and formal eligibility from the pre-action state. A missing or false `completion_confirmed` halts the episode without changing its copied state. An ineligible or unknown action also halts it. When confirmation and eligibility are both present, the runner delegates to `apply_action`; its `applied_effects` are recorded as the action's known guaranteed effects, and the report returns the final copied account state.

The runner does not estimate elapsed time, random drops, combat victories, minigame results, or unobserved quest outcomes. It does not modify either input file.
