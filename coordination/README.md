# Persistent Task Coordination

## Roles

### Orchestrator

The active Codex task owns project planning, repository integration, factual
validation, and route decisions. It reads the repository before acting and
keeps facts separate from strategy.

### Guide specialist

A persistent ChatGPT or Codex task holds the full B0aty and BRUHsailer guides in
context. It answers bounded source-analysis questions. It does not independently
select the project route or change repository files.

### Temporary workers

Subagents handle bounded, parallel work with a clear output and write scope.
Their conclusions must land in the repository before they are dismissed. They
are execution capacity, not project memory.

## Durable memory rule

No task is the sole owner of an important conclusion. Guide evidence, decisions,
assumptions, unresolved questions, and citations must be written into the
repository. Conversation context accelerates work but is not canonical storage.

## Consultation workflow

1. The orchestrator identifies a decision blocked by guide-wide context.
2. It sends the persistent specialist one bounded request using the template.
3. The specialist returns source step references, downstream effects,
   uncertainties, and a recommendation limited to the question.
4. The orchestrator checks the answer against current facts and project goals.
5. The orchestrator records accepted evidence in the appropriate research file
   or a consultation record.
6. Route changes still require the union-first omission gates.

The user should not need to relay messages between tasks. The orchestrator uses
the Codex task tools to read and message the registered specialist directly.

## When to consult

Consult the guide specialist for:

- downstream uses hidden much later in either guide;
- why a source guide chooses a quantity, threshold, or ordering;
- cross-guide comparisons spanning many banks or chapters;
- whether moving or removing a step breaks a later source bundle;
- guide-specific assumptions such as HCIM safety, maxing, PvM rush, alts,
  multiskilling, or Wintertodt policy.

Do not consult it for current prices, requirements, mechanics, drop rates, or
release changes. Verify those with official OSRS or current OSRS Wiki sources.

## Request template

```text
Consultation ID: <stable-id>
Decision blocked: <one sentence>
Project goal: efficient enjoyment of all content at useful timing; no 99 solely
for abstract efficiency.
Source scope: <B0aty banks/episodes and BRUHsailer steps/chapters>
Question: <one bounded question>

Return:
1. Relevant steps from each guide.
2. State produced: items, GP, XP, levels, quests, unlocks, travel, or safety.
3. Every named downstream consumer you can trace.
4. What breaks if the action is moved, replaced, or omitted.
5. Guide assumptions that may not fit this project.
6. Uncertainty and the minimum safe comparison horizon.

Do not design the final route. Do not infer current game mechanics from guide
text. Keep the response compact and source-referenced.
```

## Local registry

The active specialist task ID is stored in
`.codex-coordination.local.json`. That file is ignored by Git because task IDs
are local coordination metadata. `specialists.example.json` documents its
shape.

