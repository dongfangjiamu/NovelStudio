from __future__ import annotations

from typing import Any

from novel_app.state import NovelState


def feedback_ingest(state: NovelState, runtime: Any = None) -> dict:
    chapter_no = ((state.get("current_card") or {}).get("chapter_no")) or 1
    return {
        "feedback_summary": {
            "chapter_no": chapter_no,
            "immediate_actions": [],
            "observe": [],
            "discard": [],
        },
        "latest_review_reports": list(state.get("review_reports", [])),
        "chapters_completed": state.get("chapters_completed", 0) + 1,
        "rewrite_count": 0,
        "review_reports": [],
        "event_log": [f"feedback_ingested:{chapter_no}"],
    }
