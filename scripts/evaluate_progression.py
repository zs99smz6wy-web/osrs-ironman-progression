from __future__ import annotations

import argparse
import copy
from datetime import datetime
from functools import lru_cache
import json
from pathlib import Path
import re
from typing import Any

from osrs_xp import MAX_XP, SKILLS, level_from_xp


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ACTIONS = ROOT / "data" / "progression" / "actions.json"
DEFAULT_STATE = ROOT / "graph" / "account-state.example.json"
REQUIRED_STATE_KEYS = {
    "skills", "skill_xp", "quests_completed", "completed_actions", "transport_flags", "milestones",
    "gear_thresholds", "items", "resources", "counters", "passive_loops", "recurring_observations",
    "kingdom_observation", "combat_readiness_observation", "encounter_observations",
    "slayer_task", "unique_item_observations", "sailing_observation", "perilous_moons_observation",
    "farming_recurrence_observation", "diary_tiers", "kourend_memoir",
    "attention_window", "notable_drops", "preferences", "cash_commitments",
}
LIST_STATE_KEYS = {
    "quests_completed", "completed_actions", "transport_flags", "milestones",
    "gear_thresholds", "notable_drops",
}
RECURRING_OBSERVATION_FIELDS = {"state", "observed_at", "ready_at"}
RECURRING_OBSERVATION_STATES = {"needs_inputs", "in_progress", "ready", "cooldown", "unknown"}
KINGDOM_OBSERVATION_FIELDS = {
    "approval_percent", "worker_assignments", "collection_paused", "observed_at",
}
COMBAT_READINESS_FIELDS = {
    "observed_at", "loadouts", "current_hitpoints", "current_prayer",
    "food_healing_available", "prayer_restore_points_available",
    "emergency_teleport_available", "recovery_tolerance",
}
COMBAT_LOADOUT_STYLES = {"melee", "ranged", "magic"}
RECOVERY_TOLERANCES = {"none", "low", "moderate", "high"}
ENCOUNTER_OBSERVATION_FIELDS = {
    "observed_at", "attempts", "successful_completions", "elapsed_minutes",
    "supply_use", "deaths", "banking_trips",
}
UNIQUE_ITEM_OBSERVATION_FIELDS = {
    "observed_at", "possession", "collection_log", "quantity", "variant", "charges",
    "condition", "usable", "reclaimable",
}
UNIQUE_ITEM_POSSESSION_STATES = {"unknown", "owned", "not_owned"}
COLLECTION_LOG_STATES = {"unknown", "confirmed", "not_confirmed"}
UNIQUE_ITEM_CONDITIONS = {"pristine", "degraded", "broken"}
SAILING_OBSERVATION_FIELDS = {"observed_at", "vessel", "recovery", "tasks"}
SAILING_VESSEL_FIELDS = {
    "boat_type", "component_tiers", "facilities", "hull_hitpoints", "hull_max_hitpoints",
    "cargo_hold", "last_gangplank", "last_mooring_point",
}
SAILING_RECOVERY_FIELDS = {"last_event", "cargo_loss_observed"}
SAILING_TASK_FIELDS = {
    "task_id", "kind", "origin", "destination", "cargo_item", "cargo_quantity", "bounty_target",
    "bounty_item_count", "slots_used", "status", "cargo_loaded", "observed_at",
}
SAILING_TASK_KINDS = {"courier", "bounty", "unknown"}
SAILING_RECOVERY_EVENTS = {"unknown", "none", "capsize", "quick_transport", "ship_recovery", "death"}
SAILING_TASK_STATUSES = {"unknown", "accepted", "completed", "cancelled", "failed", "recovered"}
MOON_BOSS_IDS = {"blood_moon", "blue_moon", "eclipse_moon"}
PERILOUS_MOONS_OBSERVATION_FIELDS = {"observed_at", "run", "internal_supplies", "death_recovery"}
MOONS_RUN_FIELDS = {"run_id", "bosses_defeated", "defeat_order", "campsite_location", "lunar_chest_opened", "inside_neyzpotli"}
MOONS_INTERNAL_SUPPLY_FIELDS = {
    "raw_bream", "cooked_bream", "moss_lizard", "moonlight_grub_paste", "moonlight_potion", "moth",
}
MOONS_DEATH_RECOVERY_FIELDS = {"last_death_observed_at", "grave_location", "grave_active_minutes_remaining", "reclaim_status"}
MOONS_RECLAIM_STATUSES = {"unknown", "in_grave", "recovered", "expired", "deaths_office"}
FARMING_RECURRENCE_FIELDS = {"observed_at", "patches", "hespori", "anima_patch"}
FARMING_PATCH_FIELDS = {
    "patch_id", "patch_type", "seed_id", "planted_at", "growth_class", "growth_ticks_observed",
    "disease_state", "harvest_lives_remaining", "compost_id", "protection_state", "ready_observed", "observed_at",
}
FARMING_DISEASE_STATES = {"unknown", "disease_free", "diseased", "dead", "cleared"}
FARMING_PROTECTION_STATES = {"unknown", "protected", "unprotected", "not_applicable"}
HESPORI_OBSERVATION_FIELDS = {"seed_present", "planted_at", "state", "last_defeat_at", "last_harvest_at", "ready_observed"}
HESPORI_STATES = {"unknown", "seeded", "growing", "ready", "defeated", "harvested"}
ANIMA_PATCH_FIELDS = {"seed_id", "planted_at", "state", "active_effect", "ready_observed"}
ANIMA_PATCH_STATES = {"unknown", "active", "expired", "cleared"}
DIARY_TASK_OBSERVATION_COMMON_FIELDS = {"observed_at", "status", "mode", "completion_confirmed"}
DIARY_TASK_OBSERVATION_STATUSES = {"unknown", "in_progress", "completed", "reset"}
DIARY_TASK_OBSERVATION_MODES = {"combat", "rng", "crop", "daily", "charge", "team", "staged"}
DIARY_TASK_OBSERVATION_MODE_FIELDS = {
    "combat": {"encounter_key", "qualifying_successes"},
    "rng": {"qualifying_event_confirmed", "unique_item_observation_key"},
    "crop": {"patch_id", "ready_observed", "harvest_confirmed"},
    "daily": {"capability_key", "availability_state", "ready_at"},
    "charge": {"item_observation_key", "charges_before", "charges_after"},
    "team": {"activity_key", "role", "credit_or_points"},
    "staged": {"stage_ids", "completed_stage_ids", "invalidated_by_diary_update", "reset_observed_at"},
}
WILDERNESS_ELITE_BIG_THREE_TASK_KEY = "diary-task:wilderness:wilderness-elite-kill-big-three"
WILDERNESS_ELITE_BIG_THREE_STAGE_IDS = (
    "callisto_or_artio",
    "venenatis_or_spindel",
    "vetion_or_calvarion",
)
MINIGAME_ACTIVITY_IDS = frozenset({
    "barbarian-assault", "fishing-trawler", "giants-foundry", "guardians-of-the-rift",
    "hallowed-sepulchre", "last-man-standing", "mage-training-arena", "mahogany-homes",
    "motherlode-mine", "nightmare-zone", "pest-control", "pyramid-plunder", "rogues-den",
    "shades-of-mortton", "tempoross", "tithe-farm", "wintertodt",
})
MINIGAME_ACTIVITY_OBSERVATION_FIELDS = {
    "observed_at", "availability", "session", "currency_balances", "confirmed_purchases",
    "local_supplies", "charge_states", "cooldown_observations", "activity_results",
    "collection_log_rows",
}
MINIGAME_AVAILABILITY_FIELDS = {"world", "world_state", "team_state", "team_size", "location"}
MINIGAME_SESSION_FIELDS = {"status", "mode", "round_or_floor", "started_at", "last_event"}
MINIGAME_BALANCE_FIELDS = {"currency_id", "amount", "capacity"}
MINIGAME_PURCHASE_FIELDS = {"purchase_id", "quantity", "currency_spent", "observed_at"}
MINIGAME_RESULT_FIELDS = {
    "event_id", "outcome", "observed_at", "point_delta", "reported_xp", "reported_items",
}
MINIGAME_CHARGE_FIELDS = {"charge_id", "amount", "capacity", "observed_at"}
MINIGAME_COOLDOWN_FIELDS = {
    "cooldown_id", "status", "ready_at", "uses_since_reset", "daily_limit", "observed_at",
}
MINIGAME_COLLECTION_LOG_FIELDS = {"entry_id", "status", "observed_at"}
MINIGAME_WORLD_STATES = {"unknown", "available", "unavailable", "closing"}
MINIGAME_TEAM_STATES = {
    "unknown", "solo", "queueing", "available", "assembled", "in_progress", "unavailable",
}
MINIGAME_SESSION_STATES = {
    "unknown", "not_started", "queued", "active", "ended", "reset", "unavailable",
}
MINIGAME_RESULT_OUTCOMES = {"unknown", "success", "failure", "left", "death", "interrupted"}
MINIGAME_COOLDOWN_STATES = {"unknown", "ready", "cooldown", "unavailable"}
MINIGAME_ACTIVITY_CURRENCIES = {
    "barbarian-assault": frozenset({
        "currency:barbarian-assault:attacker-honour",
        "currency:barbarian-assault:collector-honour",
        "currency:barbarian-assault:defender-honour",
        "currency:barbarian-assault:healer-honour",
    }),
    "fishing-trawler": frozenset(),
    "giants-foundry": frozenset({"currency:foundry-reputation", "currency:coins"}),
    "guardians-of-the-rift": frozenset({
        "currency:gotr-elemental-points", "currency:gotr-catalytic-points", "currency:abyssal-pearls",
    }),
    "hallowed-sepulchre": frozenset({"currency:hallowed-sepulchre:marks"}),
    "last-man-standing": frozenset({"currency:last-man-standing:points", "currency:coins"}),
    "mage-training-arena": frozenset({
        "currency:mta-telekinetic-pizazz", "currency:mta-graveyard-pizazz",
        "currency:mta-enchantment-pizazz", "currency:mta-alchemist-pizazz",
    }),
    "mahogany-homes": frozenset({"currency:mahogany-homes:carpenter-points"}),
    "motherlode-mine": frozenset({"currency:golden-nuggets"}),
    "nightmare-zone": frozenset({"currency:nightmare-zone:points", "currency:coins"}),
    "pest-control": frozenset({"currency:pest-control:commendation-points", "currency:coins"}),
    "pyramid-plunder": frozenset(),
    "rogues-den": frozenset(),
    "shades-of-mortton": frozenset(),
    "tempoross": frozenset({"currency:tempoross-reward-permits"}),
    "tithe-farm": frozenset({"currency:tithe-farm-points"}),
    "wintertodt": frozenset({"currency:wintertodt:reward-cart-rolls"}),
}
MINIGAME_BALANCE_CAPACITIES = {
    ("barbarian-assault", "currency:barbarian-assault:attacker-honour"): 5000,
    ("barbarian-assault", "currency:barbarian-assault:collector-honour"): 5000,
    ("barbarian-assault", "currency:barbarian-assault:defender-honour"): 5000,
    ("barbarian-assault", "currency:barbarian-assault:healer-honour"): 5000,
    ("mage-training-arena", "currency:mta-telekinetic-pizazz"): 8000,
    ("mage-training-arena", "currency:mta-graveyard-pizazz"): 8000,
    ("mage-training-arena", "currency:mta-enchantment-pizazz"): 32000,
    ("mage-training-arena", "currency:mta-alchemist-pizazz"): 16000,
    ("pest-control", "currency:pest-control:commendation-points"): 4000,
    ("tempoross", "currency:tempoross-reward-permits"): 8000,
    ("tithe-farm", "currency:tithe-farm-points"): 16000,
    ("wintertodt", "currency:wintertodt:reward-cart-rolls"): 8000,
}
MINIGAME_ACTIVITY_CHARGES = {
    "guardians-of-the-rift": frozenset({"ring-of-the-elements-charges"}),
    "hallowed-sepulchre": frozenset({"ring-of-endurance-stamina"}),
    "nightmare-zone": frozenset({"potion-barrel-doses"}),
    "pyramid-plunder": frozenset({"pharaohs-sceptre"}),
    "shades-of-mortton": frozenset({"sacred-oil-doses"}),
    "tempoross": frozenset({"tome-of-water-pages"}),
    "tithe-farm": frozenset({"gricollers-can-doses"}),
    "wintertodt": frozenset({"rejuvenation-potion-doses"}),
}
MINIGAME_CHARGE_CAPACITIES = {
    ("guardians-of-the-rift", "ring-of-the-elements-charges"): 10000,
    ("hallowed-sepulchre", "ring-of-endurance-stamina"): 1000,
    ("nightmare-zone", "potion-barrel-doses"): 255,
    ("tithe-farm", "gricollers-can-doses"): 1000,
}
MINIGAME_CHARGE_ALLOWED_CAPACITIES = {
    ("pyramid-plunder", "pharaohs-sceptre"): frozenset({3, 10, 25, 50, 100}),
}
MINIGAME_ACTIVITY_COOLDOWNS = {
    "fishing-trawler": frozenset({"minigame-teleport"}),
    "guardians-of-the-rift": frozenset({"minigame-teleport"}),
    "last-man-standing": frozenset({"daily-forfeit"}),
    "nightmare-zone": frozenset({"grouping-teleport"}),
    "tempoross": frozenset({"minigame-teleport"}),
    "wintertodt": frozenset({"minigame-teleport"}),
}
SLAYER_TASK_FIELDS = {
    "target", "remaining", "initial_count", "master", "streak", "points",
    "blocked_targets", "observed_at",
}
DIARY_REGIONS = (
    "Ardougne",
    "Desert",
    "Falador",
    "Fremennik",
    "Kandarin",
    "Karamja",
    "Kourend & Kebos",
    "Lumbridge & Draynor",
    "Morytania",
    "Varrock",
    "Western Provinces",
    "Wilderness",
)
DIARY_TIER_ORDER = {"none": 0, "easy": 1, "medium": 2, "hard": 3, "elite": 4}
KOUREND_MEMOIR_FORMS = {"memoirs", "book_of_the_dead"}
KOUREND_MEMOIR_ORDINARY_PAGES = (
    "lunch_by_the_lancalliums",
    "the_fishers_flute",
    "history_and_hearsay",
    "jewellery_of_jubilation",
    "a_dark_disposition",
)
KOUREND_MEMOIR_SECRET_PAGE = "secret_page"
KOUREND_MEMOIR_PAGES = frozenset((*KOUREND_MEMOIR_ORDINARY_PAGES, KOUREND_MEMOIR_SECRET_PAGE))
KOUREND_MEMOIR_FIELDS = {"form", "pages", "charges"}
KOUREND_MEMOIR_OWNED_KEY = "kourend_memoir"
RFC_3339_TIMESTAMP = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)


def load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache
def diary_task_catalog() -> tuple[frozenset[str], frozenset[str]]:
    """Read canonical task keys from the integrated factual diary records."""
    regions: set[str] = set()
    task_keys: set[str] = set()
    for path in sorted((ROOT / "data" / "facts").glob("diary-factual-*.json")):
        document = load_json(path)
        for record in document.get("records", []):
            record_id = record.get("id") if isinstance(record, dict) else None
            if not isinstance(record_id, str) or not record_id.startswith("diary-factual-"):
                continue
            region_slug = record_id.removeprefix("diary-factual-")
            task_records = record.get("tasks", record.get("task_records", []))
            if not isinstance(task_records, list):
                continue
            regions.add(region_slug)
            for task in task_records:
                if not isinstance(task, dict):
                    continue
                task_id = task.get("source_task_id", task.get("package_task_id"))
                if not isinstance(task_id, str):
                    continue
                key = task.get("canonical_task_key", f"diary-task:{region_slug}:{task_id}")
                if isinstance(key, str):
                    task_keys.add(key)
    return frozenset(regions), frozenset(task_keys)


def _is_rfc_3339_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value or not RFC_3339_TIMESTAMP.fullmatch(value):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def kourend_memoir_capacity(memoir: dict[str, Any]) -> int:
    """Return the usable charge cap for a validated memoir record."""
    if memoir["form"] == "book_of_the_dead":
        return 250
    ordinary_pages = set(memoir["pages"]) & set(KOUREND_MEMOIR_ORDINARY_PAGES)
    return 20 * len(ordinary_pages)


def _validate_nullable_non_negative_integer(value: Any, context: str) -> None:
    if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
        raise ValueError(f"{context} must be a non-negative integer or null")


def _validate_nullable_trimmed_string(value: Any, context: str) -> None:
    if value is not None and (not isinstance(value, str) or not value.strip() or value != value.strip()):
        raise ValueError(f"{context} must be a non-empty trimmed string or null")


def _validate_supply_counts(values: Any, context: str) -> None:
    if not isinstance(values, dict):
        raise ValueError(f"{context} must be an object")
    for item_id, count in values.items():
        if not isinstance(item_id, str) or not item_id.strip() or item_id != item_id.strip():
            raise ValueError(f"{context} has an invalid item ID")
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError(f"{context}.{item_id} must be a non-negative integer")


def _validate_nullable_supply_counts(values: Any, context: str) -> None:
    if not isinstance(values, dict):
        raise ValueError(f"{context} must be an object")
    for item_id, count in values.items():
        if not isinstance(item_id, str) or not item_id.strip() or item_id != item_id.strip():
            raise ValueError(f"{context} has an invalid item ID")
        _validate_nullable_non_negative_integer(count, f"{context}.{item_id}")


def _validate_trimmed_string(value: Any, context: str) -> None:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{context} must be a non-empty trimmed string")


def _validate_nullable_timestamp(value: Any, context: str) -> None:
    if value is not None and not _is_rfc_3339_timestamp(value):
        raise ValueError(f"{context} must be RFC 3339 or null")


def _validate_nullable_boolean(value: Any, context: str) -> None:
    if value is not None and not isinstance(value, bool):
        raise ValueError(f"{context} must be boolean or null")


def _validate_unique_trimmed_strings(values: Any, context: str) -> None:
    if (
        not isinstance(values, list)
        or any(not isinstance(value, str) or not value.strip() or value != value.strip() for value in values)
        or len(values) != len(set(values))
    ):
        raise ValueError(f"{context} must be unique trimmed strings")


def _validate_diary_task_observations(observations: Any) -> None:
    if observations is None:
        return
    if not isinstance(observations, dict):
        raise ValueError("Account state diary_task_observations must be an object when supplied")

    region_slugs, canonical_task_keys = diary_task_catalog()
    for task_key, observation in observations.items():
        context = f"Account state diary_task_observations.{task_key}"
        if not isinstance(task_key, str) or not task_key.strip() or task_key != task_key.strip():
            raise ValueError("Account state diary_task_observations has an invalid task key")
        task_key_parts = task_key.split(":", 2)
        if len(task_key_parts) != 3 or task_key_parts[0] != "diary-task" or not task_key_parts[2]:
            raise ValueError(f"{context} must use a canonical diary-task:<region>:<task> key")
        if task_key_parts[1] not in region_slugs:
            raise ValueError(f"{context} has an invalid diary region")
        if task_key not in canonical_task_keys:
            raise ValueError(f"{context} references an unknown diary task")
        if not isinstance(observation, dict):
            raise ValueError(f"{context} must be an object")

        mode = observation.get("mode")
        expected_fields = DIARY_TASK_OBSERVATION_COMMON_FIELDS | DIARY_TASK_OBSERVATION_MODE_FIELDS.get(mode, set())
        if mode not in DIARY_TASK_OBSERVATION_MODES or set(observation) != expected_fields:
            raise ValueError(f"{context} has invalid fields for its observation mode")
        if not _is_rfc_3339_timestamp(observation["observed_at"]):
            raise ValueError(f"{context}.observed_at must be RFC 3339")
        status = observation["status"]
        if status not in DIARY_TASK_OBSERVATION_STATUSES:
            raise ValueError(f"{context}.status is invalid")
        _validate_nullable_boolean(observation["completion_confirmed"], f"{context}.completion_confirmed")
        if status == "completed" and observation["completion_confirmed"] is not True:
            raise ValueError(f"{context}.completed status requires completion_confirmed true")
        if status != "completed" and observation["completion_confirmed"] is True:
            raise ValueError(f"{context}.completion_confirmed true requires completed status")
        if status == "unknown" and observation["completion_confirmed"] is not None:
            raise ValueError(f"{context}.unknown status requires null completion_confirmed")

        if mode == "combat":
            _validate_nullable_trimmed_string(observation["encounter_key"], f"{context}.encounter_key")
            _validate_nullable_non_negative_integer(
                observation["qualifying_successes"], f"{context}.qualifying_successes"
            )
        elif mode == "rng":
            _validate_nullable_boolean(
                observation["qualifying_event_confirmed"], f"{context}.qualifying_event_confirmed"
            )
            _validate_nullable_trimmed_string(
                observation["unique_item_observation_key"], f"{context}.unique_item_observation_key"
            )
        elif mode == "crop":
            _validate_nullable_trimmed_string(observation["patch_id"], f"{context}.patch_id")
            _validate_nullable_boolean(observation["ready_observed"], f"{context}.ready_observed")
            _validate_nullable_boolean(observation["harvest_confirmed"], f"{context}.harvest_confirmed")
        elif mode == "daily":
            _validate_nullable_trimmed_string(observation["capability_key"], f"{context}.capability_key")
            if observation["availability_state"] is not None and observation["availability_state"] not in RECURRING_OBSERVATION_STATES:
                raise ValueError(f"{context}.availability_state is invalid")
            _validate_nullable_timestamp(observation["ready_at"], f"{context}.ready_at")
        elif mode == "charge":
            _validate_nullable_trimmed_string(
                observation["item_observation_key"], f"{context}.item_observation_key"
            )
            _validate_nullable_non_negative_integer(observation["charges_before"], f"{context}.charges_before")
            _validate_nullable_non_negative_integer(observation["charges_after"], f"{context}.charges_after")
        elif mode == "team":
            _validate_nullable_trimmed_string(observation["activity_key"], f"{context}.activity_key")
            _validate_nullable_trimmed_string(observation["role"], f"{context}.role")
            _validate_nullable_non_negative_integer(observation["credit_or_points"], f"{context}.credit_or_points")
        else:
            _validate_unique_trimmed_strings(observation["stage_ids"], f"{context}.stage_ids")
            completed_stage_ids = observation["completed_stage_ids"]
            if (
                not isinstance(completed_stage_ids, list)
                or any(
                    not isinstance(stage_id, str) or not stage_id.strip() or stage_id != stage_id.strip()
                    for stage_id in completed_stage_ids
                )
                or len(completed_stage_ids) != len(set(completed_stage_ids))
                or not set(completed_stage_ids).issubset(observation["stage_ids"])
            ):
                raise ValueError(f"{context}.completed_stage_ids must be a unique subset of stage_ids")
            _validate_nullable_boolean(
                observation["invalidated_by_diary_update"], f"{context}.invalidated_by_diary_update"
            )
            _validate_nullable_timestamp(observation["reset_observed_at"], f"{context}.reset_observed_at")
            reset_observed = observation["reset_observed_at"] is not None
            invalidated = observation["invalidated_by_diary_update"]
            if status == "reset" and (invalidated is not True or not reset_observed):
                raise ValueError(f"{context}.reset status requires an observed diary-update invalidation")
            if status != "reset" and (invalidated is True or reset_observed):
                raise ValueError(f"{context}.diary-update invalidation requires reset status")
            if status == "completed" and set(completed_stage_ids) != set(observation["stage_ids"]):
                raise ValueError(f"{context}.completed staged status requires every declared stage")

        if task_key == WILDERNESS_ELITE_BIG_THREE_TASK_KEY:
            if mode != "staged":
                raise ValueError(f"{context} must use staged observation mode")
            if tuple(observation["stage_ids"]) != WILDERNESS_ELITE_BIG_THREE_STAGE_IDS:
                raise ValueError(f"{context}.stage_ids must match the three Wilderness boss families")


def _validate_minigame_currency_records(
    records: Any,
    activity_id: str,
    context: str,
) -> None:
    if not isinstance(records, list):
        raise ValueError(f"{context} must be an array")
    seen_currency_ids: set[str] = set()
    allowed_currency_ids = MINIGAME_ACTIVITY_CURRENCIES[activity_id]
    for index, record in enumerate(records):
        record_context = f"{context}[{index}]"
        if not isinstance(record, dict) or set(record) != MINIGAME_BALANCE_FIELDS:
            raise ValueError(f"{record_context} has invalid fields")
        currency_id = record["currency_id"]
        _validate_trimmed_string(currency_id, f"{record_context}.currency_id")
        if currency_id not in allowed_currency_ids:
            raise ValueError(f"{record_context}.currency_id is not valid for {activity_id}")
        if currency_id in seen_currency_ids:
            raise ValueError(f"{context} must not repeat a currency ID")
        seen_currency_ids.add(currency_id)
        for field in ("amount", "capacity"):
            _validate_nullable_non_negative_integer(record[field], f"{record_context}.{field}")
        amount = record["amount"]
        capacity = record["capacity"]
        if amount is not None and capacity is not None and amount > capacity:
            raise ValueError(f"{record_context}.amount cannot exceed capacity")
        known_capacity = MINIGAME_BALANCE_CAPACITIES.get((activity_id, currency_id))
        if known_capacity is not None:
            if capacity is not None and capacity != known_capacity:
                raise ValueError(f"{record_context}.capacity must be {known_capacity} when supplied")
            if amount is not None and amount > known_capacity:
                raise ValueError(f"{record_context}.amount cannot exceed known capacity {known_capacity}")


def _validate_minigame_activity_observations(observations: Any) -> None:
    if observations is None:
        return
    if not isinstance(observations, dict):
        raise ValueError("Account state minigame_activity_observations must be an object when supplied")

    for activity_id, observation in observations.items():
        context = f"Account state minigame_activity_observations.{activity_id}"
        if activity_id not in MINIGAME_ACTIVITY_IDS:
            raise ValueError(f"{context} has an unknown minigame activity ID")
        if not isinstance(observation, dict) or "observed_at" not in observation:
            raise ValueError(f"{context} must be an observation object with observed_at")
        if not set(observation).issubset(MINIGAME_ACTIVITY_OBSERVATION_FIELDS):
            raise ValueError(f"{context} has invalid fields")
        if not _is_rfc_3339_timestamp(observation["observed_at"]):
            raise ValueError(f"{context}.observed_at must be RFC 3339")

        availability = observation.get("availability")
        if availability is not None:
            availability_context = f"{context}.availability"
            if not isinstance(availability, dict) or not set(availability).issubset(MINIGAME_AVAILABILITY_FIELDS):
                raise ValueError(f"{availability_context} has invalid fields")
            if "world" in availability:
                world = availability["world"]
                if world is not None and (isinstance(world, bool) or not isinstance(world, int) or world < 1):
                    raise ValueError(f"{availability_context}.world must be a positive integer or null")
            if "world_state" in availability and availability["world_state"] not in MINIGAME_WORLD_STATES:
                raise ValueError(f"{availability_context}.world_state is invalid")
            if "team_state" in availability and availability["team_state"] not in MINIGAME_TEAM_STATES:
                raise ValueError(f"{availability_context}.team_state is invalid")
            if "team_size" in availability:
                team_size = availability["team_size"]
                if team_size is not None and (isinstance(team_size, bool) or not isinstance(team_size, int) or team_size < 1):
                    raise ValueError(f"{availability_context}.team_size must be a positive integer or null")
            if "location" in availability:
                _validate_nullable_trimmed_string(availability["location"], f"{availability_context}.location")

        session = observation.get("session")
        if session is not None:
            session_context = f"{context}.session"
            if not isinstance(session, dict) or not set(session).issubset(MINIGAME_SESSION_FIELDS):
                raise ValueError(f"{session_context} has invalid fields")
            if "status" in session and session["status"] not in MINIGAME_SESSION_STATES:
                raise ValueError(f"{session_context}.status is invalid")
            for field in ("mode", "last_event"):
                if field in session:
                    _validate_nullable_trimmed_string(session[field], f"{session_context}.{field}")
            if "round_or_floor" in session:
                _validate_nullable_non_negative_integer(session["round_or_floor"], f"{session_context}.round_or_floor")
            if "started_at" in session:
                _validate_nullable_timestamp(session["started_at"], f"{session_context}.started_at")

        if "currency_balances" in observation:
            _validate_minigame_currency_records(
                observation["currency_balances"], activity_id, f"{context}.currency_balances"
            )

        if "confirmed_purchases" in observation:
            purchases = observation["confirmed_purchases"]
            if not isinstance(purchases, list):
                raise ValueError(f"{context}.confirmed_purchases must be an array")
            for index, purchase in enumerate(purchases):
                purchase_context = f"{context}.confirmed_purchases[{index}]"
                if not isinstance(purchase, dict) or set(purchase) != MINIGAME_PURCHASE_FIELDS:
                    raise ValueError(f"{purchase_context} has invalid fields")
                _validate_trimmed_string(purchase["purchase_id"], f"{purchase_context}.purchase_id")
                quantity = purchase["quantity"]
                if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
                    raise ValueError(f"{purchase_context}.quantity must be a positive integer")
                if not _is_rfc_3339_timestamp(purchase["observed_at"]):
                    raise ValueError(f"{purchase_context}.observed_at must be RFC 3339")
                _validate_minigame_currency_records(
                    purchase["currency_spent"], activity_id, f"{purchase_context}.currency_spent"
                )

        if "local_supplies" in observation:
            _validate_nullable_supply_counts(observation["local_supplies"], f"{context}.local_supplies")

        if "charge_states" in observation:
            charges = observation["charge_states"]
            if not isinstance(charges, list):
                raise ValueError(f"{context}.charge_states must be an array")
            seen_charge_ids: set[str] = set()
            allowed_charge_ids = MINIGAME_ACTIVITY_CHARGES.get(activity_id, frozenset())
            for index, charge in enumerate(charges):
                charge_context = f"{context}.charge_states[{index}]"
                if not isinstance(charge, dict) or set(charge) != MINIGAME_CHARGE_FIELDS:
                    raise ValueError(f"{charge_context} has invalid fields")
                charge_id = charge["charge_id"]
                _validate_trimmed_string(charge_id, f"{charge_context}.charge_id")
                if charge_id not in allowed_charge_ids:
                    raise ValueError(f"{charge_context}.charge_id is not valid for {activity_id}")
                if charge_id in seen_charge_ids:
                    raise ValueError(f"{context}.charge_states must not repeat a charge ID")
                seen_charge_ids.add(charge_id)
                for field in ("amount", "capacity"):
                    _validate_nullable_non_negative_integer(charge[field], f"{charge_context}.{field}")
                amount = charge["amount"]
                capacity = charge["capacity"]
                if amount is not None and capacity is not None and amount > capacity:
                    raise ValueError(f"{charge_context}.amount cannot exceed capacity")
                known_capacity = MINIGAME_CHARGE_CAPACITIES.get((activity_id, charge_id))
                if known_capacity is not None:
                    if capacity is not None and capacity != known_capacity:
                        raise ValueError(f"{charge_context}.capacity must be {known_capacity} when supplied")
                    if amount is not None and amount > known_capacity:
                        raise ValueError(f"{charge_context}.amount cannot exceed known capacity {known_capacity}")
                allowed_capacities = MINIGAME_CHARGE_ALLOWED_CAPACITIES.get((activity_id, charge_id))
                if capacity is not None and allowed_capacities is not None and capacity not in allowed_capacities:
                    raise ValueError(f"{charge_context}.capacity is not a supported observed capacity")
                if not _is_rfc_3339_timestamp(charge["observed_at"]):
                    raise ValueError(f"{charge_context}.observed_at must be RFC 3339")

        if "cooldown_observations" in observation:
            cooldowns = observation["cooldown_observations"]
            if not isinstance(cooldowns, list):
                raise ValueError(f"{context}.cooldown_observations must be an array")
            seen_cooldown_ids: set[str] = set()
            allowed_cooldown_ids = MINIGAME_ACTIVITY_COOLDOWNS.get(activity_id, frozenset())
            for index, cooldown in enumerate(cooldowns):
                cooldown_context = f"{context}.cooldown_observations[{index}]"
                if not isinstance(cooldown, dict) or set(cooldown) != MINIGAME_COOLDOWN_FIELDS:
                    raise ValueError(f"{cooldown_context} has invalid fields")
                cooldown_id = cooldown["cooldown_id"]
                _validate_trimmed_string(cooldown_id, f"{cooldown_context}.cooldown_id")
                if cooldown_id not in allowed_cooldown_ids:
                    raise ValueError(f"{cooldown_context}.cooldown_id is not valid for {activity_id}")
                if cooldown_id in seen_cooldown_ids:
                    raise ValueError(f"{context}.cooldown_observations must not repeat a cooldown ID")
                seen_cooldown_ids.add(cooldown_id)
                if cooldown["status"] not in MINIGAME_COOLDOWN_STATES:
                    raise ValueError(f"{cooldown_context}.status is invalid")
                _validate_nullable_timestamp(cooldown["ready_at"], f"{cooldown_context}.ready_at")
                _validate_nullable_non_negative_integer(
                    cooldown["uses_since_reset"], f"{cooldown_context}.uses_since_reset"
                )
                daily_limit = cooldown["daily_limit"]
                if daily_limit is not None and (
                    isinstance(daily_limit, bool) or not isinstance(daily_limit, int) or daily_limit < 1
                ):
                    raise ValueError(f"{cooldown_context}.daily_limit must be a positive integer or null")
                uses_since_reset = cooldown["uses_since_reset"]
                if uses_since_reset is not None and daily_limit is not None and uses_since_reset > daily_limit:
                    raise ValueError(f"{cooldown_context}.uses_since_reset cannot exceed daily_limit")
                if cooldown["status"] != "cooldown" and cooldown["ready_at"] is not None:
                    raise ValueError(f"{cooldown_context}.ready_at requires cooldown status")
                if not _is_rfc_3339_timestamp(cooldown["observed_at"]):
                    raise ValueError(f"{cooldown_context}.observed_at must be RFC 3339")

        if "activity_results" in observation:
            results = observation["activity_results"]
            if not isinstance(results, list):
                raise ValueError(f"{context}.activity_results must be an array")
            seen_event_ids: set[str] = set()
            for index, result in enumerate(results):
                result_context = f"{context}.activity_results[{index}]"
                if not isinstance(result, dict) or set(result) != MINIGAME_RESULT_FIELDS:
                    raise ValueError(f"{result_context} has invalid fields")
                event_id = result["event_id"]
                _validate_trimmed_string(event_id, f"{result_context}.event_id")
                if event_id in seen_event_ids:
                    raise ValueError(f"{context}.activity_results must not repeat an event ID")
                seen_event_ids.add(event_id)
                if result["outcome"] not in MINIGAME_RESULT_OUTCOMES:
                    raise ValueError(f"{result_context}.outcome is invalid")
                if not _is_rfc_3339_timestamp(result["observed_at"]):
                    raise ValueError(f"{result_context}.observed_at must be RFC 3339")
                _validate_nullable_non_negative_integer(result["point_delta"], f"{result_context}.point_delta")
                for field in ("reported_xp", "reported_items"):
                    _validate_nullable_supply_counts(result[field], f"{result_context}.{field}")
                if result["outcome"] == "unknown" and (
                    result["point_delta"] is not None or result["reported_xp"] or result["reported_items"]
                ):
                    raise ValueError(f"{result_context}.unknown outcome cannot report generated outputs")

        if "collection_log_rows" in observation:
            rows = observation["collection_log_rows"]
            if not isinstance(rows, list):
                raise ValueError(f"{context}.collection_log_rows must be an array")
            seen_entry_ids: set[str] = set()
            for index, row in enumerate(rows):
                row_context = f"{context}.collection_log_rows[{index}]"
                if not isinstance(row, dict) or set(row) != MINIGAME_COLLECTION_LOG_FIELDS:
                    raise ValueError(f"{row_context} has invalid fields")
                entry_id = row["entry_id"]
                _validate_trimmed_string(entry_id, f"{row_context}.entry_id")
                if entry_id in seen_entry_ids:
                    raise ValueError(f"{context}.collection_log_rows must not repeat an entry ID")
                seen_entry_ids.add(entry_id)
                if row["status"] not in COLLECTION_LOG_STATES:
                    raise ValueError(f"{row_context}.status is invalid")
                if not _is_rfc_3339_timestamp(row["observed_at"]):
                    raise ValueError(f"{row_context}.observed_at must be RFC 3339")


def validate_account_state(state: dict[str, Any]) -> None:
    missing = REQUIRED_STATE_KEYS - state.keys()
    if missing:
        raise ValueError(f"Account state missing required keys: {sorted(missing)}")

    for key in LIST_STATE_KEYS:
        values = state[key]
        if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
            raise ValueError(f"Account state {key} must be an array of strings")
        if len(values) != len(set(values)):
            raise ValueError(f"Account state {key} must not contain duplicates")

    for key in ("skills", "skill_xp", "items", "resources", "counters"):
        values = state[key]
        if not isinstance(values, dict):
            raise ValueError(f"Account state {key} must be an object")
        for name, value in values.items():
            minimum = 1 if key == "skills" else 0
            maximum = 99 if key == "skills" else MAX_XP if key == "skill_xp" else None
            if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
                raise ValueError(f"Account state {key}.{name} has an invalid value")
            if maximum is not None and value > maximum:
                raise ValueError(f"Account state {key}.{name} has an invalid value")

    expected_skills = set(SKILLS)
    for key in ("skills", "skill_xp"):
        actual_skills = set(state[key])
        if actual_skills != expected_skills:
            missing_skills = sorted(expected_skills - actual_skills)
            unknown_skills = sorted(actual_skills - expected_skills)
            raise ValueError(
                f"Account state {key} must contain every supported skill exactly; "
                f"missing={missing_skills}, unknown={unknown_skills}"
            )
    for skill in SKILLS:
        derived_level = level_from_xp(state["skill_xp"][skill])
        if state["skills"][skill] != derived_level:
            raise ValueError(
                f"Account state {skill} level {state['skills'][skill]} does not match "
                f"XP-derived level {derived_level}"
            )

    passive_loops = state["passive_loops"]
    if not isinstance(passive_loops, dict) or any(not isinstance(value, bool) for value in passive_loops.values()):
        raise ValueError("Account state passive_loops must contain boolean values")

    observations = state["recurring_observations"]
    if not isinstance(observations, dict):
        raise ValueError("Account state recurring_observations must be an object")
    for system_id, observation in observations.items():
        if system_id not in passive_loops:
            raise ValueError(f"Account state recurring_observations.{system_id} is not a known passive loop")
        if not isinstance(observation, dict) or set(observation) != RECURRING_OBSERVATION_FIELDS:
            raise ValueError(f"Account state recurring_observations.{system_id} has invalid fields")
        if observation["state"] not in RECURRING_OBSERVATION_STATES:
            raise ValueError(f"Account state recurring_observations.{system_id}.state is invalid")
        if not _is_rfc_3339_timestamp(observation["observed_at"]):
            raise ValueError(f"Account state recurring_observations.{system_id}.observed_at must be RFC 3339")
        if observation["ready_at"] is not None and not _is_rfc_3339_timestamp(observation["ready_at"]):
            raise ValueError(f"Account state recurring_observations.{system_id}.ready_at must be RFC 3339 or null")

    kingdom_observation = state["kingdom_observation"]
    if kingdom_observation is not None:
        if not passive_loops.get("kingdom", False):
            raise ValueError("Account state kingdom_observation requires passive_loops.kingdom to be true")
        if not isinstance(kingdom_observation, dict) or set(kingdom_observation) != KINGDOM_OBSERVATION_FIELDS:
            raise ValueError("Account state kingdom_observation has invalid fields")

        approval = kingdom_observation["approval_percent"]
        if isinstance(approval, bool) or not isinstance(approval, int) or not 25 <= approval <= 100:
            raise ValueError("Account state kingdom_observation.approval_percent must be an integer from 25 to 100")

        assignments = kingdom_observation["worker_assignments"]
        if not isinstance(assignments, dict):
            raise ValueError("Account state kingdom_observation.worker_assignments must be an object")
        worker_total = 0
        for category, workers in assignments.items():
            if not isinstance(category, str) or not category.strip():
                raise ValueError("Account state kingdom_observation.worker_assignments has an invalid category")
            if isinstance(workers, bool) or not isinstance(workers, int) or workers < 0 or workers > 10:
                raise ValueError(
                    f"Account state kingdom_observation.worker_assignments.{category} must be an integer from 0 to 10"
                )
            worker_total += workers
        worker_limit = 15 if "Royal Trouble" in state["quests_completed"] else 10
        if worker_total > worker_limit:
            raise ValueError(
                f"Account state kingdom_observation.worker_assignments total must not exceed {worker_limit}"
            )

        if not isinstance(kingdom_observation["collection_paused"], bool):
            raise ValueError("Account state kingdom_observation.collection_paused must be boolean")
        if not _is_rfc_3339_timestamp(kingdom_observation["observed_at"]):
            raise ValueError("Account state kingdom_observation.observed_at must be RFC 3339")

    combat_readiness = state["combat_readiness_observation"]
    if combat_readiness is not None:
        if not isinstance(combat_readiness, dict) or set(combat_readiness) != COMBAT_READINESS_FIELDS:
            raise ValueError("Account state combat_readiness_observation has invalid fields")
        if not _is_rfc_3339_timestamp(combat_readiness["observed_at"]):
            raise ValueError("Account state combat_readiness_observation.observed_at must be RFC 3339")
        loadouts = combat_readiness["loadouts"]
        if not isinstance(loadouts, dict) or set(loadouts) != COMBAT_LOADOUT_STYLES:
            raise ValueError("Account state combat_readiness_observation.loadouts must contain melee, ranged, and magic")
        for style, item_ids in loadouts.items():
            if (
                not isinstance(item_ids, list)
                or any(not isinstance(item_id, str) or not item_id.strip() or item_id != item_id.strip() for item_id in item_ids)
                or len(item_ids) != len(set(item_ids))
            ):
                raise ValueError(
                    f"Account state combat_readiness_observation.loadouts.{style} must be unique trimmed item IDs"
                )
        for field in (
            "current_hitpoints", "current_prayer", "food_healing_available", "prayer_restore_points_available",
        ):
            _validate_nullable_non_negative_integer(
                combat_readiness[field], f"Account state combat_readiness_observation.{field}"
            )
        if combat_readiness["emergency_teleport_available"] is not None and not isinstance(
            combat_readiness["emergency_teleport_available"], bool
        ):
            raise ValueError("Account state combat_readiness_observation.emergency_teleport_available must be boolean or null")
        if (
            combat_readiness["recovery_tolerance"] is not None
            and combat_readiness["recovery_tolerance"] not in RECOVERY_TOLERANCES
        ):
            raise ValueError("Account state combat_readiness_observation.recovery_tolerance is invalid")

    encounter_observations = state["encounter_observations"]
    if not isinstance(encounter_observations, dict):
        raise ValueError("Account state encounter_observations must be an object")
    for encounter_id, observation in encounter_observations.items():
        if not isinstance(encounter_id, str) or not encounter_id.strip() or encounter_id != encounter_id.strip():
            raise ValueError("Account state encounter_observations has an invalid encounter ID")
        if not isinstance(observation, dict) or set(observation) != ENCOUNTER_OBSERVATION_FIELDS:
            raise ValueError(f"Account state encounter_observations.{encounter_id} has invalid fields")
        if not _is_rfc_3339_timestamp(observation["observed_at"]):
            raise ValueError(f"Account state encounter_observations.{encounter_id}.observed_at must be RFC 3339")
        attempts = observation["attempts"]
        if isinstance(attempts, bool) or not isinstance(attempts, int) or attempts < 0:
            raise ValueError(f"Account state encounter_observations.{encounter_id}.attempts must be a non-negative integer")
        for field in ("successful_completions", "elapsed_minutes", "deaths", "banking_trips"):
            _validate_nullable_non_negative_integer(
                observation[field], f"Account state encounter_observations.{encounter_id}.{field}"
            )
        successes = observation["successful_completions"]
        if successes is not None and successes > attempts:
            raise ValueError(
                f"Account state encounter_observations.{encounter_id}.successful_completions cannot exceed attempts"
            )
        _validate_supply_counts(observation["supply_use"], f"Account state encounter_observations.{encounter_id}.supply_use")

    slayer_task = state["slayer_task"]
    if slayer_task is not None:
        if not isinstance(slayer_task, dict) or set(slayer_task) != SLAYER_TASK_FIELDS:
            raise ValueError("Account state slayer_task has invalid fields")
        target = slayer_task["target"]
        if not isinstance(target, str) or not target or target != target.strip():
            raise ValueError("Account state slayer_task.target must be a non-empty trimmed string")
        remaining = slayer_task["remaining"]
        if isinstance(remaining, bool) or not isinstance(remaining, int) or remaining < 1:
            raise ValueError("Account state slayer_task.remaining must be a positive integer")
        if not _is_rfc_3339_timestamp(slayer_task["observed_at"]):
            raise ValueError("Account state slayer_task.observed_at must be RFC 3339")
        _validate_nullable_non_negative_integer(slayer_task["initial_count"], "Account state slayer_task.initial_count")
        if slayer_task["initial_count"] is not None and slayer_task["initial_count"] < remaining:
            raise ValueError("Account state slayer_task.initial_count cannot be below remaining")
        _validate_nullable_trimmed_string(slayer_task["master"], "Account state slayer_task.master")
        for field in ("streak", "points"):
            _validate_nullable_non_negative_integer(slayer_task[field], f"Account state slayer_task.{field}")
        blocked_targets = slayer_task["blocked_targets"]
        if (
            not isinstance(blocked_targets, list)
            or any(not isinstance(target, str) or not target.strip() or target != target.strip() for target in blocked_targets)
            or len(blocked_targets) != len(set(blocked_targets))
        ):
            raise ValueError("Account state slayer_task.blocked_targets must be unique trimmed target names")

    unique_item_observations = state["unique_item_observations"]
    if not isinstance(unique_item_observations, dict):
        raise ValueError("Account state unique_item_observations must be an object")
    for item_id, observation in unique_item_observations.items():
        if not isinstance(item_id, str) or not item_id.strip() or item_id != item_id.strip():
            raise ValueError("Account state unique_item_observations has an invalid item ID")
        if not isinstance(observation, dict) or set(observation) != UNIQUE_ITEM_OBSERVATION_FIELDS:
            raise ValueError(f"Account state unique_item_observations.{item_id} has invalid fields")
        if not _is_rfc_3339_timestamp(observation["observed_at"]):
            raise ValueError(f"Account state unique_item_observations.{item_id}.observed_at must be RFC 3339")
        if observation["possession"] not in UNIQUE_ITEM_POSSESSION_STATES:
            raise ValueError(f"Account state unique_item_observations.{item_id}.possession is invalid")
        if observation["collection_log"] not in COLLECTION_LOG_STATES:
            raise ValueError(f"Account state unique_item_observations.{item_id}.collection_log is invalid")
        _validate_nullable_non_negative_integer(
            observation["quantity"], f"Account state unique_item_observations.{item_id}.quantity"
        )
        _validate_nullable_trimmed_string(observation["variant"], f"Account state unique_item_observations.{item_id}.variant")
        _validate_nullable_non_negative_integer(
            observation["charges"], f"Account state unique_item_observations.{item_id}.charges"
        )
        if observation["condition"] is not None and observation["condition"] not in UNIQUE_ITEM_CONDITIONS:
            raise ValueError(f"Account state unique_item_observations.{item_id}.condition is invalid")
        for field in ("usable", "reclaimable"):
            if observation[field] is not None and not isinstance(observation[field], bool):
                raise ValueError(f"Account state unique_item_observations.{item_id}.{field} must be boolean or null")
        if observation["possession"] == "owned" and observation["quantity"] is not None and observation["quantity"] < 1:
            raise ValueError(f"Account state unique_item_observations.{item_id}.owned quantity must be positive")
        if observation["possession"] == "unknown" and observation["quantity"] is not None:
            raise ValueError(f"Account state unique_item_observations.{item_id}.unknown possession requires null quantity")

    sailing = state["sailing_observation"]
    if sailing is not None:
        if not isinstance(sailing, dict) or set(sailing) != SAILING_OBSERVATION_FIELDS:
            raise ValueError("Account state sailing_observation has invalid fields")
        if not _is_rfc_3339_timestamp(sailing["observed_at"]):
            raise ValueError("Account state sailing_observation.observed_at must be RFC 3339")

        vessel = sailing["vessel"]
        if not isinstance(vessel, dict) or set(vessel) != SAILING_VESSEL_FIELDS:
            raise ValueError("Account state sailing_observation.vessel has invalid fields")
        _validate_nullable_trimmed_string(vessel["boat_type"], "Account state sailing_observation.vessel.boat_type")
        component_tiers = vessel["component_tiers"]
        if not isinstance(component_tiers, dict):
            raise ValueError("Account state sailing_observation.vessel.component_tiers must be an object")
        for component_id, tier in component_tiers.items():
            if not isinstance(component_id, str) or not component_id.strip() or component_id != component_id.strip():
                raise ValueError("Account state sailing_observation.vessel.component_tiers has an invalid component ID")
            _validate_nullable_non_negative_integer(
                tier, f"Account state sailing_observation.vessel.component_tiers.{component_id}"
            )
        _validate_unique_trimmed_strings(
            vessel["facilities"], "Account state sailing_observation.vessel.facilities"
        )
        for field in ("hull_hitpoints", "hull_max_hitpoints"):
            _validate_nullable_non_negative_integer(
                vessel[field], f"Account state sailing_observation.vessel.{field}"
            )
        if (
            vessel["hull_hitpoints"] is not None
            and vessel["hull_max_hitpoints"] is not None
            and vessel["hull_hitpoints"] > vessel["hull_max_hitpoints"]
        ):
            raise ValueError("Account state sailing_observation.vessel.hull_hitpoints cannot exceed hull_max_hitpoints")
        _validate_supply_counts(vessel["cargo_hold"], "Account state sailing_observation.vessel.cargo_hold")
        for field in ("last_gangplank", "last_mooring_point"):
            _validate_nullable_trimmed_string(
                vessel[field], f"Account state sailing_observation.vessel.{field}"
            )

        recovery = sailing["recovery"]
        if not isinstance(recovery, dict) or set(recovery) != SAILING_RECOVERY_FIELDS:
            raise ValueError("Account state sailing_observation.recovery has invalid fields")
        if recovery["last_event"] not in SAILING_RECOVERY_EVENTS:
            raise ValueError("Account state sailing_observation.recovery.last_event is invalid")
        _validate_nullable_boolean(
            recovery["cargo_loss_observed"], "Account state sailing_observation.recovery.cargo_loss_observed"
        )

        tasks = sailing["tasks"]
        if not isinstance(tasks, list):
            raise ValueError("Account state sailing_observation.tasks must be an array")
        seen_task_ids: set[str] = set()
        for index, task in enumerate(tasks):
            context = f"Account state sailing_observation.tasks[{index}]"
            if not isinstance(task, dict) or set(task) != SAILING_TASK_FIELDS:
                raise ValueError(f"{context} has invalid fields")
            task_id = task["task_id"]
            if not isinstance(task_id, str) or not task_id.strip() or task_id != task_id.strip():
                raise ValueError(f"{context}.task_id must be a non-empty trimmed string")
            if task_id in seen_task_ids:
                raise ValueError("Account state sailing_observation.tasks must have unique task IDs")
            seen_task_ids.add(task_id)
            if task["kind"] not in SAILING_TASK_KINDS:
                raise ValueError(f"{context}.kind is invalid")
            for field in ("origin", "destination", "cargo_item", "bounty_target"):
                _validate_nullable_trimmed_string(task[field], f"{context}.{field}")
            for field in ("cargo_quantity", "bounty_item_count", "slots_used"):
                _validate_nullable_non_negative_integer(task[field], f"{context}.{field}")
            if task["status"] not in SAILING_TASK_STATUSES:
                raise ValueError(f"{context}.status is invalid")
            _validate_nullable_boolean(task["cargo_loaded"], f"{context}.cargo_loaded")
            if not _is_rfc_3339_timestamp(task["observed_at"]):
                raise ValueError(f"{context}.observed_at must be RFC 3339")

    moons = state["perilous_moons_observation"]
    if moons is not None:
        if not isinstance(moons, dict) or set(moons) != PERILOUS_MOONS_OBSERVATION_FIELDS:
            raise ValueError("Account state perilous_moons_observation has invalid fields")
        if not _is_rfc_3339_timestamp(moons["observed_at"]):
            raise ValueError("Account state perilous_moons_observation.observed_at must be RFC 3339")

        run = moons["run"]
        if not isinstance(run, dict) or set(run) != MOONS_RUN_FIELDS:
            raise ValueError("Account state perilous_moons_observation.run has invalid fields")
        _validate_nullable_trimmed_string(run["run_id"], "Account state perilous_moons_observation.run.run_id")
        for field in ("bosses_defeated", "defeat_order"):
            _validate_unique_trimmed_strings(run[field], f"Account state perilous_moons_observation.run.{field}")
            if any(boss_id not in MOON_BOSS_IDS for boss_id in run[field]):
                raise ValueError(f"Account state perilous_moons_observation.run.{field} has an invalid Moon ID")
        if not set(run["defeat_order"]).issubset(run["bosses_defeated"]):
            raise ValueError("Account state perilous_moons_observation.run.defeat_order must be a subset of bosses_defeated")
        _validate_nullable_trimmed_string(
            run["campsite_location"], "Account state perilous_moons_observation.run.campsite_location"
        )
        for field in ("lunar_chest_opened", "inside_neyzpotli"):
            _validate_nullable_boolean(run[field], f"Account state perilous_moons_observation.run.{field}")

        internal_supplies = moons["internal_supplies"]
        if not isinstance(internal_supplies, dict) or set(internal_supplies) != MOONS_INTERNAL_SUPPLY_FIELDS:
            raise ValueError("Account state perilous_moons_observation.internal_supplies has invalid fields")
        for item_id, quantity in internal_supplies.items():
            _validate_nullable_non_negative_integer(
                quantity, f"Account state perilous_moons_observation.internal_supplies.{item_id}"
            )

        death_recovery = moons["death_recovery"]
        if not isinstance(death_recovery, dict) or set(death_recovery) != MOONS_DEATH_RECOVERY_FIELDS:
            raise ValueError("Account state perilous_moons_observation.death_recovery has invalid fields")
        _validate_nullable_timestamp(
            death_recovery["last_death_observed_at"],
            "Account state perilous_moons_observation.death_recovery.last_death_observed_at",
        )
        _validate_nullable_trimmed_string(
            death_recovery["grave_location"],
            "Account state perilous_moons_observation.death_recovery.grave_location",
        )
        _validate_nullable_non_negative_integer(
            death_recovery["grave_active_minutes_remaining"],
            "Account state perilous_moons_observation.death_recovery.grave_active_minutes_remaining",
        )
        if death_recovery["reclaim_status"] not in MOONS_RECLAIM_STATUSES:
            raise ValueError("Account state perilous_moons_observation.death_recovery.reclaim_status is invalid")

    farming = state["farming_recurrence_observation"]
    if farming is not None:
        if not isinstance(farming, dict) or set(farming) != FARMING_RECURRENCE_FIELDS:
            raise ValueError("Account state farming_recurrence_observation has invalid fields")
        if not _is_rfc_3339_timestamp(farming["observed_at"]):
            raise ValueError("Account state farming_recurrence_observation.observed_at must be RFC 3339")

        patches = farming["patches"]
        if not isinstance(patches, list):
            raise ValueError("Account state farming_recurrence_observation.patches must be an array")
        seen_patch_ids: set[str] = set()
        for index, patch in enumerate(patches):
            context = f"Account state farming_recurrence_observation.patches[{index}]"
            if not isinstance(patch, dict) or set(patch) != FARMING_PATCH_FIELDS:
                raise ValueError(f"{context} has invalid fields")
            for field in ("patch_id", "patch_type"):
                value = patch[field]
                if not isinstance(value, str) or not value.strip() or value != value.strip():
                    raise ValueError(f"{context}.{field} must be a non-empty trimmed string")
            if patch["patch_id"] in seen_patch_ids:
                raise ValueError("Account state farming_recurrence_observation.patches must have unique patch IDs")
            seen_patch_ids.add(patch["patch_id"])
            for field in ("seed_id", "growth_class", "compost_id"):
                _validate_nullable_trimmed_string(patch[field], f"{context}.{field}")
            _validate_nullable_timestamp(patch["planted_at"], f"{context}.planted_at")
            for field in ("growth_ticks_observed", "harvest_lives_remaining"):
                _validate_nullable_non_negative_integer(patch[field], f"{context}.{field}")
            if patch["disease_state"] not in FARMING_DISEASE_STATES:
                raise ValueError(f"{context}.disease_state is invalid")
            if patch["protection_state"] not in FARMING_PROTECTION_STATES:
                raise ValueError(f"{context}.protection_state is invalid")
            _validate_nullable_boolean(patch["ready_observed"], f"{context}.ready_observed")
            if not _is_rfc_3339_timestamp(patch["observed_at"]):
                raise ValueError(f"{context}.observed_at must be RFC 3339")

        hespori = farming["hespori"]
        if hespori is not None:
            if not isinstance(hespori, dict) or set(hespori) != HESPORI_OBSERVATION_FIELDS:
                raise ValueError("Account state farming_recurrence_observation.hespori has invalid fields")
            _validate_nullable_boolean(
                hespori["seed_present"], "Account state farming_recurrence_observation.hespori.seed_present"
            )
            for field in ("planted_at", "last_defeat_at", "last_harvest_at"):
                _validate_nullable_timestamp(
                    hespori[field], f"Account state farming_recurrence_observation.hespori.{field}"
                )
            if hespori["state"] not in HESPORI_STATES:
                raise ValueError("Account state farming_recurrence_observation.hespori.state is invalid")
            _validate_nullable_boolean(
                hespori["ready_observed"], "Account state farming_recurrence_observation.hespori.ready_observed"
            )

        anima = farming["anima_patch"]
        if anima is not None:
            if not isinstance(anima, dict) or set(anima) != ANIMA_PATCH_FIELDS:
                raise ValueError("Account state farming_recurrence_observation.anima_patch has invalid fields")
            for field in ("seed_id", "active_effect"):
                _validate_nullable_trimmed_string(
                    anima[field], f"Account state farming_recurrence_observation.anima_patch.{field}"
                )
            _validate_nullable_timestamp(
                anima["planted_at"], "Account state farming_recurrence_observation.anima_patch.planted_at"
            )
            if anima["state"] not in ANIMA_PATCH_STATES:
                raise ValueError("Account state farming_recurrence_observation.anima_patch.state is invalid")
            _validate_nullable_boolean(
                anima["ready_observed"], "Account state farming_recurrence_observation.anima_patch.ready_observed"
            )

    diary_tiers = state["diary_tiers"]
    if not isinstance(diary_tiers, dict) or set(diary_tiers) != set(DIARY_REGIONS):
        raise ValueError("Account state diary_tiers must contain every canonical region exactly")
    for region, tier in diary_tiers.items():
        if tier not in DIARY_TIER_ORDER:
            raise ValueError(f"Account state diary_tiers.{region} has an invalid tier")

    _validate_diary_task_observations(state.get("diary_task_observations"))
    _validate_minigame_activity_observations(state.get("minigame_activity_observations"))

    kourend_memoir = state["kourend_memoir"]
    if kourend_memoir is not None:
        if not isinstance(kourend_memoir, dict) or set(kourend_memoir) != KOUREND_MEMOIR_FIELDS:
            raise ValueError("Account state kourend_memoir has invalid fields")
        if kourend_memoir["form"] not in KOUREND_MEMOIR_FORMS:
            raise ValueError("Account state kourend_memoir.form is invalid")
        pages = kourend_memoir["pages"]
        if (
            not isinstance(pages, list)
            or any(page not in KOUREND_MEMOIR_PAGES for page in pages)
            or len(pages) != len(set(pages))
        ):
            raise ValueError("Account state kourend_memoir.pages must be unique canonical page IDs")
        charges = kourend_memoir["charges"]
        if isinstance(charges, bool) or not isinstance(charges, int) or charges < 0:
            raise ValueError("Account state kourend_memoir.charges must be a non-negative integer")
        if (
            kourend_memoir["form"] == "book_of_the_dead"
            and not set(KOUREND_MEMOIR_ORDINARY_PAGES).issubset(pages)
        ):
            raise ValueError("Account state kourend_memoir.book_of_the_dead requires all ordinary pages")
        capacity = kourend_memoir_capacity(kourend_memoir)
        if charges > capacity:
            raise ValueError(
                f"Account state kourend_memoir.charges must not exceed capacity {capacity}"
            )

    attention = state["attention_window"]
    if not isinstance(attention, dict) or attention.get("mode") not in {"true_afk", "low_attention", "semi_afk", "active"}:
        raise ValueError("Account state attention_window has an invalid mode")
    duration = attention.get("duration_minutes")
    if isinstance(duration, bool) or not isinstance(duration, int) or duration < 1:
        raise ValueError("Account state attention_window has an invalid duration")
    if not isinstance(attention.get("player_present"), bool):
        raise ValueError("Account state attention_window.player_present must be boolean")

    preferences = state["preferences"]
    for key in ("risk_tolerance", "intensity_tolerance", "diversity_preference"):
        value = preferences.get(key) if isinstance(preferences, dict) else None
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 4:
            raise ValueError(f"Account state preferences.{key} must be an integer from 0 to 4")

    commitments = state["cash_commitments"]
    if not isinstance(commitments, list):
        raise ValueError("Account state cash_commitments must be an array")
    valid_deadlines = {"now", "next_goal", "near_term", "later"}
    for index, commitment in enumerate(commitments):
        if not isinstance(commitment, dict) or set(commitment) != {"purpose", "coins", "deadline"}:
            raise ValueError(f"Account state cash_commitments[{index}] has invalid fields")
        if not isinstance(commitment["purpose"], str) or not commitment["purpose"].strip():
            raise ValueError(f"Account state cash_commitments[{index}].purpose must be non-empty")
        coins = commitment["coins"]
        if isinstance(coins, bool) or not isinstance(coins, int) or coins < 0:
            raise ValueError(f"Account state cash_commitments[{index}].coins has an invalid value")
        if commitment["deadline"] not in valid_deadlines:
            raise ValueError(f"Account state cash_commitments[{index}].deadline is invalid")


def _predicate_result(predicate: dict[str, Any], state: dict[str, Any]) -> tuple[bool, str]:
    predicate_type = predicate["type"]
    key = predicate["key"]
    value = predicate.get("value")

    if predicate_type == "skill_at_least":
        current = state.get("skills", {}).get(key, 1)
        return current >= value, f"{key} {value} (current: {current})"
    if predicate_type == "resource_at_least":
        current = state.get("resources", {}).get(key, 0)
        return current >= value, f"{value} {key} (current: {current})"
    if predicate_type == "item_at_least":
        current = state.get("items", {}).get(key, 0)
        return current >= value, f"{value} x {key} (current: {current})"
    if predicate_type == "counter_at_least":
        current = state.get("counters", {}).get(key, 0)
        return current >= value, f"{key} {value} (current: {current})"
    if predicate_type == "quest_completed":
        return key in state.get("quests_completed", []), f"complete {key}"
    if predicate_type == "transport_flag":
        return key in state.get("transport_flags", []), f"unlock transport: {key}"
    if predicate_type == "transport_flag_absent":
        absent = key not in state.get("transport_flags", [])
        return absent, f"transport remains locked: {key}"
    if predicate_type == "milestone":
        return key in state.get("milestones", []), f"reach milestone: {key}"
    if predicate_type == "passive_loop":
        expected = value if value is not None else True
        current = state.get("passive_loops", {}).get(key, False)
        return current is expected, f"passive loop {key} = {str(expected).lower()}"
    if predicate_type == "recurring_state":
        current = state.get("recurring_observations", {}).get(key, {}).get("state", "unobserved")
        return current == value, f"recurring state {key} = {value} (current: {current})"
    if predicate_type == "slayer_task_target":
        task = state.get("slayer_task")
        current = task["target"] if task is not None and task["remaining"] > 0 else "none"
        return current == key, f"current Slayer task {key} (current: {current})"
    if predicate_type == "diary_tier_at_least":
        current = state["diary_tiers"][key]
        return (
            DIARY_TIER_ORDER[current] >= DIARY_TIER_ORDER[value],
            f"{key} diary {value} (confirmed: {current})",
        )
    if predicate_type == "kourend_memoir_owned":
        owned = state["kourend_memoir"] is not None
        return owned, f"own Kourend memoir (current: {'owned' if owned else 'none'})"
    if predicate_type == "kourend_memoir_form":
        memoir = state["kourend_memoir"]
        current = memoir["form"] if memoir is not None else "none"
        return current == key, f"Kourend memoir form {key} (current: {current})"
    if predicate_type == "kourend_memoir_page":
        memoir = state["kourend_memoir"]
        has_page = memoir is not None and key in memoir["pages"]
        return has_page, f"Kourend memoir page {key}"
    if predicate_type == "kourend_memoir_charges_at_least":
        memoir = state["kourend_memoir"]
        current = memoir["charges"] if memoir is not None else 0
        return current >= value, f"Kourend memoir charges {value} (current: {current})"
    if predicate_type == "kourend_memoir_charge_space_at_least":
        memoir = state["kourend_memoir"]
        current = kourend_memoir_capacity(memoir) - memoir["charges"] if memoir is not None else 0
        return current >= value, f"Kourend memoir charge space {value} (current: {current})"
    if predicate_type == "notable_drop":
        return key in state.get("notable_drops", []), f"obtain notable drop: {key}"
    if predicate_type == "gear_threshold":
        return key in state.get("gear_thresholds", []), f"reach gear threshold: {key}"
    raise ValueError(f"Unknown predicate type: {predicate_type}")


def evaluate_condition(condition: dict[str, Any], state: dict[str, Any]) -> tuple[bool, list[str]]:
    if "all" in condition:
        missing: list[str] = []
        for child in condition["all"]:
            satisfied, child_missing = evaluate_condition(child, state)
            if not satisfied:
                missing.extend(child_missing)
        return not missing, missing

    if "any" in condition:
        alternatives: list[list[str]] = []
        for child in condition["any"]:
            satisfied, child_missing = evaluate_condition(child, state)
            if satisfied:
                return True, []
            alternatives.append(child_missing)
        rendered = " OR ".join(" + ".join(parts) for parts in alternatives)
        return False, [f"one of: {rendered}"]

    satisfied, description = _predicate_result(condition, state)
    return satisfied, [] if satisfied else [description]


def evaluate_actions(actions_document: dict[str, Any], account_state: dict[str, Any]) -> list[dict[str, Any]]:
    validate_account_state(account_state)
    results: list[dict[str, Any]] = []
    for action in actions_document["actions"]:
        satisfied, missing = evaluate_condition(action["requirements"], account_state)
        prepared, missing_preparation = evaluate_condition(action["preparation"], account_state)
        completion_satisfied, _ = evaluate_condition(action["completion"], account_state)
        completed = not action["repeatable"] and (
            action["id"] in account_state.get("completed_actions", []) or completion_satisfied
        )
        if completed:
            status = "completed"
        elif not satisfied:
            status = "blocked"
        elif not prepared:
            status = "needs_preparation"
        else:
            status = "eligible"
        results.append(
            {
                "id": action["id"],
                "name": action["name"],
                "kind": action["kind"],
                "status": status,
                "missing": [] if completed else missing,
                "missing_preparation": [] if completed else missing_preparation,
                "fact_ids": action["fact_ids"],
            }
        )
    return results


def report_diary_task_observations(account_state: dict[str, Any]) -> dict[str, Any]:
    """Return imported diary-task snapshots without deriving durable progress."""
    validate_account_state(account_state)
    observations = copy.deepcopy(account_state.get("diary_task_observations", {}))
    return {
        "observations": observations,
        "observation_count": len(observations),
        "milestones_inferred": False,
        "diary_tiers_inferred": False,
        "completed_actions_inferred": False,
        "inventory_inferred": False,
        "counters_inferred": False,
        "action_eligibility_inferred": False,
        "wilderness_elite_big_three": copy.deepcopy(
            observations.get(WILDERNESS_ELITE_BIG_THREE_TASK_KEY)
        ),
        "wilderness_elite_big_three_durable_boss_kills_inferred": False,
    }


def report_minigame_activity_observations(account_state: dict[str, Any]) -> dict[str, Any]:
    """Return explicit minigame snapshots without deriving progress or outputs."""
    validate_account_state(account_state)
    observations = copy.deepcopy(account_state.get("minigame_activity_observations", {}))
    return {
        "observations": observations,
        "observation_count": len(observations),
        "activity_results_inferred": False,
        "balances_inferred": False,
        "purchases_inferred": False,
        "inventory_inferred": False,
        "xp_inferred": False,
        "collection_log_inferred": False,
        "charges_or_cooldowns_advanced": False,
        "action_eligibility_inferred": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate verified progression actions for an account state.")
    parser.add_argument("state", nargs="?", default=DEFAULT_STATE, type=Path)
    parser.add_argument("--actions", default=DEFAULT_ACTIONS, type=Path)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()

    account_state = load_json(args.state)
    results = evaluate_actions(load_json(args.actions), account_state)
    diary_observation_report = report_diary_task_observations(account_state)
    minigame_observation_report = report_minigame_activity_observations(account_state)
    if args.json:
        print(json.dumps({
            "results": results,
            "diary_task_observations": diary_observation_report,
            "minigame_activity_observations": minigame_observation_report,
        }, indent=2))
        return 0

    for result in results:
        print(f"[{result['status'].upper()}] {result['name']}")
        for missing in result["missing"]:
            print(f"  - missing: {missing}")
        for missing in result["missing_preparation"]:
            print(f"  - prepare: {missing}")
    print(f"Diary task observations: {diary_observation_report['observation_count']}")
    print("Diary task milestones inferred: false")
    print("Diary tiers inferred: false")
    print(f"Minigame activity observations: {minigame_observation_report['observation_count']}")
    print("Minigame activity outputs inferred: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
