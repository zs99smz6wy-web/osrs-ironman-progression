# Quest Unlocks And Fixed XP Windows

## Scope

This is a strategy-only timing catalog. It uses existing normalized actions and
facts; it does not select an opening, prescribe training, or make a route.

The timing labels below follow `strategy/content-window-contract.md`. Factual
gates come from the named action and fact IDs. Readiness, ideal timing, delay,
and bundle observations are strategy judgments, not hidden requirements.

## Spirit Trees And Gnome Gliders

**ID:** `window:gnome-transport`  
**Domain/status:** transport / `ready_candidate` when its action gates are met  
**Actions/facts:** `action:tree-gnome-village`, `action:grand-tree`; `tree-gnome-village`, `grand-tree`, `transport-network-audit`

- **Earliest gates:** Tree Gnome Village has no modeled skill or preparation gate. The Grand Tree requires 25 Agility.
- **Readiness:** combat, travel, supplies, and attention are not modeled as gates.
- **Ideal candidate:** compare Tree Gnome Village when spirit-tree access has a near-term geographic use. Compare The Grand Tree once 25 Agility is already met and its glider plus fixed Attack, Agility, and Magic XP can serve declared objectives.
- **Delay and later entry:** delaying postpones base spirit-tree access; delaying The Grand Tree postpones gliders and its fixed XP. A later entry remains reasonable when neither network reduces a selected bundle's travel.
- **Stop/re-entry:** stop each action at its permanent network unlock. Re-enter for the other quest when its separate gate and benefit become relevant; military gliders are a later extension, not a base requirement.
- **Outputs/alternatives:** Tree Gnome Village grants spirit-tree access and 11,450 Attack XP. The Grand Tree grants gliders, 18,400 Attack XP, 7,900 Agility XP, and 2,150 Magic XP. Player-grown and POH spirit trees are separate extensions.
- **Tags:** `kandarin`, `transport`, `fixed-xp`, `quest-handoff`.
- **Risk/attention/AFK:** no AFK claim. Practical safety and detour cost need episode-level observation.
- **Confidence:** high for gates and outputs; medium for timing value.

## Fairy-Ring Permission

**ID:** `window:fairy-ring-permission`  
**Domain/status:** transport / `blocked` until the partial-quest chain is met  
**Actions/facts:** `action:lost-city`, `action:nature-spirit`, `action:fairytale-i-growing-pains`, `action:fairy-ring-permission`; `fairy-rings`, `lost-city`, `nature-spirit`, `fairytale-i-growing-pains`, `transport-network-audit`

- **Earliest gates:** complete The Restless Ghost, Priest in Peril, Nature Spirit, Lost City, and Fairytale I. Lost City requires 31 Crafting, 36 Woodcutting, an axe, and a knife. The permission action also requires a Dramen staff, Lunar staff, or the elite Lumbridge & Draynor Diary milestone.
- **Readiness:** the Fairytale II partial-progress steps, combat, travel, and inventory are not fully normalized as an executable package.
- **Ideal candidate:** compare the permission state when ring destinations unlock several selected objectives or repeat travel. Full Fairytale II is not required for the network, so completion rewards must not be used to justify the earlier permission window.
- **Delay and later entry:** delaying preserves the option to bundle the chain with Morytania, Farming, or travel work, but postpones a broad permanent network. Re-enter later for Fairytale II completion rewards or a POH access point.
- **Stop/re-entry:** stop at `fairytale_ii_fairy_godfather_permission`; re-enter for full Fairytale II or high-Construction POH transport.
- **Outputs/alternatives:** Fairytale I grants Magic secateurs and fixed Farming, Attack, and Magic XP. Network use still needs the staff or diary exemption. A POH ring is a later access point, not an alternative to permission.
- **Tags:** `zanaris`, `morytania`, `transport`, `farming`, `fixed-xp`.
- **Risk/attention/AFK:** no AFK claim; partial-quest execution remains a coverage gap.
- **Confidence:** high for normalized gates and permission boundary; medium for bundle timing.

## Morytania Entry And Nature Spirit

**ID:** `window:morytania-entry`  
**Domain/status:** regional access / `blocked` until Priest in Peril inputs are available  
**Actions/facts:** `action:priest-in-peril`, `action:nature-spirit`; `priest-in-peril`, `nature-spirit`, `transport-network-audit`

- **Earliest gates:** Priest in Peril requires a bucket and either 50 rune essence or 50 pure essence. Nature Spirit additionally requires The Restless Ghost, Priest in Peril, a Ghostspeak amulet, and a silver sickle.
- **Readiness:** Temple Guardian handling, Morytania travel, supplies, and player risk tolerance are strategy observations.
- **Ideal candidate:** compare Priest in Peril when a selected Morytania objective needs access. Compare Nature Spirit when its utility milestone, blessed sickle, druid pouch, and fixed Crafting/Defence/Hitpoints XP have a named downstream use, including the fairy-ring chain.
- **Delay and later entry:** delaying avoids an isolated trip but delays regional access. The opening studies agree on an early Varrock start while showing that completion can be deferred; that is sequencing evidence, not a deadline.
- **Stop/re-entry:** stop Priest in Peril at `morytania`; stop Nature Spirit at `nature_spirit_utility`. Re-enter when a named Morytania quest, diary, PvM, transport, or fairy-ring dependency becomes active.
- **Outputs/alternatives:** Priest in Peril grants Morytania, Wolfbane, and 1,406 Prayer XP. Nature Spirit grants its utility milestone, silver sickle (b), druid pouch, 3,000 Crafting XP, 2,000 Defence XP, and 2,000 Hitpoints XP.
- **Tags:** `varrock`, `morytania`, `fairy-rings`, `fixed-xp`, `quest-chain`.
- **Risk/attention/AFK:** no AFK claim. Ghosts Ahoy/Ectophial are separately normalized; their later transport window is not implied by Morytania entry.
- **Confidence:** high for modeled gates and outputs; medium for timing.

## Fossil Island Access

**ID:** `window:fossil-island-access`  
**Domain/status:** regional access and transport / `blocked` until Bone Voyage closure  
**Actions/facts:** `action:the-dig-site`, `action:fossil-island-access`, `action:fossil-island-barge-trip`, `action:bind-fossil-island-pendant-destination`; `the-dig-site`, `the-dig-site-quest-detail`, `fossil-island-post-bone-voyage-barge`, `fossil-island-transport-and-camp`, `transport-network-audit`

- **Earliest gates:** The Dig Site requires 10 Agility, 10 Herblore, and 25 Thieving plus its normalized item set. Bone Voyage then requires The Dig Site, 100 Museum Kudos, two vodka, and an unfinished marrentill potion.
- **Readiness:** the model does not assert a first Fossil Island activity, combat readiness, a kudos-generation plan, or Museum Camp construction priority.
- **Ideal candidate:** compare this window when a selected Fossil Island activity, repeat barge travel, or the pendant destination has immediate use. The Dig Site is especially relevant before training beyond its modeled Agility, Herblore, and Thieving gates because it gives fixed Mining and Herblore XP.
- **Delay and later entry:** delaying avoids a separate kudos and preparation bundle; it postpones Island access and free barge quick travel. Re-enter after access to discover chosen mushtree endpoints, bind a pendant destination, or build selected Museum Camp infrastructure.
- **Stop/re-entry:** stop the access window at `fossil_island` and `fossil_island_barge_quick_travel`. Pendant binding and each mushtree discovery are separate stops; a pendant charge remains consumable.
- **Outputs/alternatives:** Bone Voyage unlocks Fossil Island and no-fare barge quick travel. The Dig Site awards 15,300 Mining XP, 2,000 Herblore XP, two gold bars, and the modeled specimen-cleaning milestone.
- **Tags:** `varrock`, `museum-kudos`, `fossil-island`, `transport`, `fixed-xp`.
- **Risk/attention/AFK:** no AFK claim. Exact kudos production and selected Island activity windows need their own records.
- **Confidence:** high for gates, barge behavior, and stated outputs; medium for timing.

## Varlamore Entry And Internal Travel

**ID:** `window:varlamore-entry`  
**Domain/status:** regional access / `ready_candidate` after Children of the Sun  
**Actions/facts:** `action:children-of-the-sun`; `children-of-the-sun`, `quest-transport`; opening-guide studies

- **Earliest gates:** Children of the Sun has no modeled skill, item, or enemy gate.
- **Readiness:** a reason to enter, chosen Varlamore activity, travel loop, and supply plan remain strategy observations.
- **Ideal candidate:** compare it during a Varrock bundle when Varlamore access has a declared nearby use. Both reviewed openings complete it during first Varrock work; BRUHsailer additionally uses an early quetzal-and-sawmill loop. This is strong execution evidence, not a universal placement.
- **Delay and later entry:** delaying has low modeled preparation cost but postpones regional access. Re-enter when a named Varlamore activity, diary, quest, or economy window is ready.
- **Stop/re-entry:** stop at the `varlamore` transport flag. Re-enter for a separately modeled internal travel or content objective.
- **Outputs/alternatives:** the normalized output is Varlamore access only. Children of the Sun explicitly does **not** grant the internal Quetzal Transport System.
- **Tags:** `varrock`, `varlamore`, `transport`, `opening-handoff`.
- **Risk/attention/AFK:** no AFK claim.
- **Coverage gap:** Twilight's Promise and its Quetzal-network permission have factual research but no normalized action in this bounded catalog; do not infer it from Children of the Sun.
- **Confidence:** high for entry boundary; medium for first-Varrock timing.

## Early POH Foundation

**ID:** `window:poh-foundation`  
**Domain/status:** permanent convenience / `ready_candidate` when ownership path is available  
**Actions/facts:** normalized POH ownership action; `poh-convenience-foundation`, `poh-relocation`, `quest-transport`; opening-guide studies

- **Earliest gates:** ownership requires Construction 1 and either 1,000 coins or the `daddys_home_completed` milestone. Teleport to House additionally needs 40 Magic. House locations have their own unboostable Construction and coin gates.
- **Readiness:** the model does not prescribe a location, room, furniture build, cash reserve, or Construction method.
- **Ideal candidate:** compare the Daddy's Home ownership path when a Varrock follow-up already needs its materials or a house is about to provide a declared convenience. Both opening studies start it in first Varrock work and finish soon after; that is empirical sequencing evidence, not proof that every account should do so.
- **Delay and later entry:** delaying preserves early coins and removes a materials relay, but postpones basic ownership. Re-enter for a chosen relocation, Teleport to House, or sourced furniture threshold.
- **Stop/re-entry:** stop the foundation window at `poh_owned`; re-enter only for a named room, location, or utility object.
- **Outputs/alternatives:** Daddy's Home is the no-1,000-coin initial-house alternative. Early ownership does not imply a portal chamber, pool, fairy ring, jewellery box, or other high-Construction feature.
- **Tags:** `varrock`, `poh`, `construction`, `permanent-convenience`, `opening-handoff`.
- **Risk/attention/AFK:** no AFK claim.
- **Coverage gap:** the repository models the completed-Daddy's-Home milestone as an ownership alternative but does not normalize its full quest action, inputs, or completion transition.
- **Confidence:** high for ownership alternatives and POH gates; medium for timing.

## Sailing Entry And First Fixed Checkpoint

**ID:** `window:sailing-entry`  
**Domain/status:** skill and regional-content access / `ready_candidate` after Pandemonium  
**Actions/facts:** `action:pandemonium`, `action:buy-sailing-skiff`, `action:sailing-bounty-task`; `sailing-entry-pandemonium`, `sailing-skiff`, `sailing-bounty-tasks`, `sailing-core`; `research/sailing-economics-timing.md`

- **Earliest gates:** Pandemonium has no modeled quest, skill, item, or coin requirement. It unlocks Sailing with 300 Sailing XP, a raft, Captain's log, and 25 sawmill coupons.
- **Readiness:** choosing Sailing for enjoyment, ship materials, a training method, or a later destination remains account-specific. No Skiff funding or shipbuilding stockpile is Pandemonium preparation.
- **Ideal candidate:** compare entry when Sailing itself is a selected experience or Port Sarim work gives it low marginal travel cost. The first modeled fixed economic checkpoint is a Skiff at 15 Sailing and 15,000 coins.
- **Delay and later entry:** there is no modeled penalty for deferring entry without a declared Sailing purpose. Re-enter the fixed-checkpoint evaluation at 15 Sailing and 15,000 coins, or when a sourced activity or upgrade has exact inputs.
- **Stop/re-entry:** stop initial entry at `sailing_access`; do not infer a next activity. Skiff ownership is a separate stop. Bounty tasks begin at 30 Sailing and remain variable-output activities.
- **Outputs/alternatives:** Pandemonium is access, not a generic transport replacement. Component inputs, selected fees, Construction gates, and later destinations are target-specific.
- **Tags:** `port-sarim`, `sailing`, `transport`, `economy`, `optional-content`.
- **Risk/attention/AFK:** no AFK claim; no passive progression claim.
- **Confidence:** high for entry and fixed Skiff gate; medium for timing.

## Fixed XP Threshold Landmarks

**ID:** `window:fixed-quest-xp-landmarks`  
**Domain/status:** one-time XP timing / `accessible_not_ready` until each action's independent gates are met  
**Actions/facts:** all actions in `research/quest-xp-threshold-sequencing.json`; `strategy/quest-xp-threshold-contexts.json`

- **Rule:** fixed XP can be compared before deliberate training crosses a modeled gate. It never cancels skill, quest, item, coin, combat, travel, or preparation blockers.
- **Combat package:** Waterfall Quest, Tree Gnome Village, and The Grand Tree provide fixed combat XP. Waterfall has no skill requirement but requires rope and elemental runes; its hazard is explicitly modeled. Tree Gnome Village and The Grand Tree additionally shape transport windows.
- **Low-gate landmarks:** The Dig Site sits behind 10 Agility, 10 Herblore, and 25 Thieving; The Grand Tree sits behind 25 Agility; Sleeping Giants sits behind 15 Smithing; Temple of the Eye sits behind 10 Runecraft and Enter the Abyss.
- **Downstream landmarks:** Nature Spirit's fixed Crafting XP is relevant before Lost City's 31 Crafting gate. The Dig Site's fixed Herblore XP is relevant before Eadgar's Ruse's 31 Herblore gate. Lost City itself still needs 36 Woodcutting.
- **Runecraft package:** Enter the Abyss provides 1,000 Runecraft XP after Rune Mysteries; Temple of the Eye then provides 9,210 Runecraft XP and Guardians of the Rift access. Entering the content and choosing ongoing training are separate decisions.
- **Transport-linked XP:** The Forsaken Tower is a Kourend minecart unlock in the normalized model, but its reward amount conflicts between existing action and audit records. Treat it as a transport window with an XP-data gap, not as a threshold calculation input.
- **Stop/re-entry:** stop at the declared fixed reward or permanent unlock. Re-enter only for a separately named reward, quest continuation, or transport extension.
- **Tags:** `quest-xp`, `threshold`, `transport`, `no-route-claim`.
- **Risk/attention/AFK:** no AFK claim. Practical readiness remains outside the analyzer.
- **Confidence:** high for the bounded action list and its no-free-XP rule; medium for threshold timing; low for any unnormalized quest or conflicting reward amount.

## Coverage Boundaries

- Player-chosen XP, including the X Marks the Spot lamp, remains unallocated and is deliberately excluded from fixed-XP timing.
- The catalog does not yet contain normalized actions for Twilight's Promise, Daddy's Home completion, or a full partial-Fairytale-II execution package.
- Museum Kudos production, individual mushtree discoveries, POH build timing, combat safety, inventory plans, and account-specific drop opportunities require their own records before episode selection.
- Proven-guide agreement is retained as execution evidence only. It neither proves an ideal window nor selects a route.
