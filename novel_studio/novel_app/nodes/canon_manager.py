from __future__ import annotations

from typing import Any

from novel_app.schemas import CanonUpdate
from novel_app.state import NovelState


def canon_commit(state: NovelState, runtime: Any = None) -> dict:
    card = state.get("current_card") or {}
    draft = state.get("current_draft") or {}
    chapter_no = card.get("chapter_no", 1)
    current_canon = state.get("canon_state") or {
        "story_clock": {"current_arc": 1, "current_chapter": 0, "in_story_time": "day_0"},
        "character_states": {},
        "open_loops": [],
    }

    delta = draft.get("canon_delta_candidate") or {}
    canon_update = CanonUpdate(
        chapter_no=chapter_no,
        character_updates=delta.get("character_updates", []),
        world_updates=[str(item) for item in delta.get("world_updates", [])],
        loop_updates=delta.get("loop_updates", []),
        summary_150=draft.get("summary_100w", "")[:150],
    )

    updated_open_loops = list(current_canon.get("open_loops", []))
    for item in canon_update.loop_updates:
        updated_open_loops.append(item)

    updated_canon = {
        **current_canon,
        "story_clock": {
            **(current_canon.get("story_clock") or {}),
            "current_chapter": chapter_no,
        },
        "last_chapter_summary": canon_update.summary_150,
        "last_canon_update": canon_update.model_dump(),
        "open_loops": updated_open_loops,
    }
    return {
        "canon_state": updated_canon,
        "event_log": [f"canon_committed:{chapter_no}"],
    }
