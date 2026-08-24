# Scoring Framework

This document contains strategy, not game facts. Scores are prompts for comparison and explanations, not an automatic substitute for judgement.

## Executable scoring layer

`strategy/candidates.json` assigns each annotated verified action a 0-4 judgement for lifetime utility, content unlock, economic infrastructure, multi-output value, diversity, AFK fit, detour cost, burnout risk, and danger risk. Coverage expands in coherent tranches; an unannotated action remains visible as eligible but unscored. General positive dimensions add; costs and risks subtract. AFK fit contributes only when the account's current attention window supports it. Diversity preference, intensity tolerance, and risk tolerance then produce explicit adjustments.

Only actions classified `eligible` by the factual evaluator may be scored. Blocked, preparation-incomplete, completed, and unverified actions are excluded. The score is a transparent comparison aid, not an optimal-route claim.

`strategy/transport-bundles.json` may add one separately named contextual point to an eligible action that establishes its own distinct durable early-transport capability while the bundle remains incomplete. It never creates a prerequisite between transport actions, and charged or consumable transport items receive context but no bundle point. See `strategy/transport-bundle.md`.

`strategy/durable-utility-item-contexts.json` groups fixed acquisition alternatives for account-long storage items. It adds no score by itself: a purchase-ready path still reports that current demand is unconfirmed, and simultaneous ready purchases that compete for the same observed currency are shown without choosing a purchase order.

## Priority hierarchy

1. Major permanent unlocks and transport.
2. Major content unlocks and hard capability gates.
3. Economic and resource infrastructure.
4. Multi-purpose experience, supplies, GP, and gear progression.
5. Collection-log, diary, and combat-achievement value with material utility.
6. Raw experience with little downstream value.

## Timing modifiers

- Lifetime utility: how often the effect will matter from this point forward.
- Detour payback: travel and setup cost versus future time saved.
- Opportunity window: earliest viable, naturally convenient, latest sensible, or always available.
- Content diversity: prefer a balanced portfolio across quests, skills, minigames, PvM, exploration, transport, and resource gathering.
- Burnout risk: avoid chaining high-monotony activities absent a strong unlock reason.
- Account reactivity: a useful unexpected drop can eliminate, defer, or re-rank a target.
- AFK fit: value depends on the player's available attention window and whether they remain present.

## GP policy

Do not use a generic cash target as a recommendation. Each future target must identify the purchases it funds, the earliest deadline, and alternatives that supply GP while advancing the account. Blackjacking is an available method, not a default doctrine.

## Collection-log policy

Collection-log progress is positive only when it coincides with a meaningful reward, capability, or naturally aligned activity. Greenlogging is not a project objective.
