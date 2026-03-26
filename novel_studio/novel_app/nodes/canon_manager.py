from __future__ import annotations

import json
from typing import Any

from novel_app.schemas import CanonUpdate
from novel_app.state import NovelState


CHARACTER_LIST_APPEND_FIELDS = {
    "known_facts_add": "known_facts",
    "active_goals_add": "active_goals",
    "injuries_add": "injuries",
    "inventory_add": "inventory",
    "hidden_from_mc_add": "hidden_from_mc",
    "relationship_delta_add": "relationship_delta",
}


def _default_canon_state() -> dict[str, Any]:
    return {
        "story_clock": {"current_arc": 1, "current_chapter": 0, "in_story_time": "day_0"},
        "character_states": {},
        "world_facts": [],
        "open_loops": [],
    }


def _dedupe_preserve_order(items: list[Any]) -> list[Any]:
    seen: set[str] = set()
    result: list[Any] = []
    for item in items:
        marker = json.dumps(item, ensure_ascii=False, sort_keys=True) if isinstance(item, (dict, list)) else str(item)
        if marker in seen:
            continue
        seen.add(marker)
        result.append(item)
    return result


def _normalize_world_update(item: Any) -> str:
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        update_type = str(item.get("type", "fact")).strip()
        value = str(item.get("value", "")).strip()
        if value:
            return f"{update_type}:{value}"
    return str(item).strip()


def _merge_character_states(current_states: dict[str, Any], updates: list[dict[str, Any]]) -> dict[str, Any]:
    merged = dict(current_states)
    for update in updates:
        character_id = str(update.get("character_id", "")).strip()
        if not character_id:
            continue
        current = dict(merged.get(character_id) or {})
        current["character_id"] = character_id
        for update_field, target_field in CHARACTER_LIST_APPEND_FIELDS.items():
            if update_field in update:
                existing_list = list(current.get(target_field, []))
                additions = update.get(update_field) or []
                current[target_field] = _dedupe_preserve_order(existing_list + list(additions))

        for field, value in update.items():
            if field == "character_id" or field in CHARACTER_LIST_APPEND_FIELDS:
                continue
            current[field] = value
        merged[character_id] = current
    return merged


def _loop_key(item: Any) -> str:
    if isinstance(item, dict) and item.get("id"):
        return str(item["id"])
    return json.dumps(item, ensure_ascii=False, sort_keys=True) if isinstance(item, (dict, list)) else str(item)


def _merge_open_loops(current_loops: list[Any], loop_updates: list[dict[str, Any]]) -> list[Any]:
    merged: dict[str, Any] = {_loop_key(item): item for item in current_loops}
    for update in loop_updates:
        key = _loop_key(update)
        status = str(update.get("status", "active")).lower()
        if status in {"resolved", "closed"}:
            merged.pop(key, None)
            continue
        merged[key] = update
    return list(merged.values())


def canon_commit(state: NovelState, runtime: Any = None) -> dict:
    del runtime

    card = state.get("current_card") or {}
    draft = state.get("current_draft") or {}
    chapter_no = card.get("chapter_no", 1)
    current_canon = state.get("canon_state") or _default_canon_state()

    delta = draft.get("canon_delta_candidate") or {}
    canon_update = CanonUpdate(
        chapter_no=chapter_no,
        character_updates=delta.get("character_updates", []),
        world_updates=[
            normalized
            for normalized in (_normalize_world_update(item) for item in delta.get("world_updates", []))
            if normalized
        ],
        loop_updates=delta.get("loop_updates", []),
        summary_150=draft.get("summary_100w", "")[:150],
    )

    merged_character_states = _merge_character_states(
        dict(current_canon.get("character_states") or {}),
        canon_update.character_updates,
    )
    merged_world_facts = _dedupe_preserve_order(
        list(current_canon.get("world_facts", [])) + list(canon_update.world_updates)
    )
    merged_open_loops = _merge_open_loops(
        list(current_canon.get("open_loops", [])),
        canon_update.loop_updates,
    )

    updated_canon = {
        **_default_canon_state(),
        **current_canon,
        "story_clock": {
            **(_default_canon_state()["story_clock"]),
            **(current_canon.get("story_clock") or {}),
            "current_chapter": chapter_no,
        },
        "character_states": merged_character_states,
        "world_facts": merged_world_facts,
        "last_chapter_summary": canon_update.summary_150,
        "last_canon_update": canon_update.model_dump(),
        "open_loops": merged_open_loops,
    }
    return {
        "canon_state": updated_canon,
        "event_log": [
            f"canon_committed:{chapter_no}",
            f"canon_loops_open:{len(merged_open_loops)}",
            f"canon_world_facts:{len(merged_world_facts)}",
        ],
    }
