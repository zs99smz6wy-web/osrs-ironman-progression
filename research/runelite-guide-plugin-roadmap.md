# RuneLite Guide Plugin Roadmap

This is a future delivery path for the progression project, not a commitment to build a Java plugin before the guide data and decision contracts are mature. The reference implementation is useful evidence for client shape and packaging; its guide order, prose, and assumptions are not imported as project truth.

## Target experience

The research pipeline generates a versioned guide JSON artifact from factual records, strategy contexts, and account-state observations. A future client can present that artifact as:

- a sidebar with the current step, purpose, requirements, alternatives, safety notes, and a manual `Done` action;
- a section picker grouped by episode, bank checkpoint, or region;
- a timeline showing completed, current, blocked, optional, and deferred content;
- progress persisted locally by guide ID and account identity, with an export/import or reset path;
- links back to the cited Wiki, official source, or community guide and, where licensed and available, the relevant episode/video.

The current-step instruction must follow the repository's concise [guide writing style](../route/guide-writing-style.md). Keep rationale, sources, and caveats available without placing them in the action sentence.

The first inspectable artifact should be an HTML preview of the existing [post-Tutorial Varrock Museum proof segment](execution-segments/post-tutorial-varrock-museum-proof.json). It should render the same coarse steps and boundaries without pretending to be a final route. Generated JSON remains the portable source for the preview, local client, tests, and eventual Plugin Hub build.

## State and progress

The plugin should consume a generated guide package, not scrape strategy prose at runtime. Each step should carry stable IDs, source IDs, purpose, requirements, account-applicability notes, alternatives, stop/re-entry conditions, and explicit completion observations. The client stores only user progress and observations: current guide version, selected section, completed step IDs, manual overrides, last-seen account fingerprint, and optional notes. A guide update must migrate by stable IDs, preserve compatible completions, and visibly mark removed or changed steps for review.

Manual completion is authoritative for coarse actions and any step the client cannot observe reliably. Auto-progress is only a convenience signal and must be reversible or require confirmation when an event is ambiguous. A player can skip, defer, undo, reset a section, or mark a step completed manually without the plugin claiming that the underlying game state is fully known.

## Conservative RuneLite observations

The initial auto-progress subset may use ordinary client-observable facts: quest completion changes exposed by the quest state, skill-level thresholds, and presence of curated item IDs in inventory, equipment, or bank when the relevant container is observable. These observations can suggest that a normalized requirement is satisfied; they cannot create a quest start, partial quest stage, reward, collection-log entry, bank transaction, or route decision. The existing Character Exporter import remains the durable account-state snapshot path, using the repository's numeric item resolver rather than display-name matching. A future plugin-side bridge may export a compatible snapshot, but it should share the import contract instead of inventing a second account model.

Do not auto-complete or estimate:

- RNG drops, chest contents, collection-log utility rewards, or monster-kill success;
- combat readiness, survival, deaths, supplies, or encounter completion;
- elapsed time, AFK duration, farming growth, daily resets, or passive production;
- partial quest stages, NPC conversations, travel, bank visits, or multi-step interactions unless an explicit RuneLite event contract proves that exact observation;
- a strategically preferred action merely because it became eligible.

Timers can be displayed as player reminders only when a current observation exists. They must never interrupt a committed quest, Slayer task, encounter, or player-selected activity, and timer readiness must not be treated as route priority.

## Delivery phases

1. **HTML preview:** define a small guide-package schema/view model, render the Museum proof JSON, show state labels and source links, and test version migration and manual completion in a browser. No Java or automatic route selection.
2. **Local RuneLite development plugin:** create a separate plugin project once the generated package and preview are stable. Bundle a pinned guide JSON, implement sidebar/current-step/timeline views, local persistence, manual completion, and read-only observations for quests, skills, and curated items. Keep the plugin adapter thin; decision logic remains in repository data and contracts.
3. **Account-state bridge:** support an explicit Character Exporter-compatible import/export workflow and account-name/version checks. Treat imported bank, inventory, equipment, quests, skills, diaries, and seed-vault data as snapshots with the same unknown and observation boundaries already used by the repository.
4. **Private dogfood:** run the new Ironman through bounded episodes, compare plugin suggestions with the HTML preview and recorded observations, and collect usability issues. Validate update migration, reset behavior, missing data, stale exports, and manual overrides before adding broader auto-progress.
5. **Plugin Hub candidate:** publish a standalone public repository with its own build, tests, icon, support URL, license, notices, generated-data provenance, and reproducible guide-data generation. Follow the current Plugin Hub submission checklist and make clear that the plugin is third-party and unaffiliated with RuneLite.

## Versioning, licensing, and attribution

Guide JSON needs a schema version, guide/content version, generated-at timestamp, source snapshot identifiers, and a human-readable change summary. Generated facts and strategy judgments must retain their existing source IDs and fact/strategy boundary. The plugin may bundle generated data only after its source licenses and attribution are reviewed; code licensing, Wiki-derived content licensing, and third-party guide/video attribution must remain separate notices. The B0aty plugin's BSD-2-Clause code and its separately attributed Wiki-derived guide data are an architectural reminder, not permission to copy code or redistribute its content. BRUHsailer and B0aty are strategy references with their own authorship and terms.

## Architectural references

- [RuneLite Plugin Hub listing](https://runelite.net/plugin-hub/show/hcim-guide-plugin): current presentation and Plugin Hub context.
- [nandobrazil/hcim-guide-plugin](https://github.com/nandobrazil/hcim-guide-plugin): implementation evidence for bundled generated guide JSON, sidebar sections, persistence, manual completion, narrow auto-progress, local development, publishing, and separate attribution.

The project should reach the Plugin Hub only after the data model, observation boundaries, and manual workflow are pleasant to use. The plugin is a delivery surface for the progression framework, not the place where the framework's strategic judgments are hidden.
