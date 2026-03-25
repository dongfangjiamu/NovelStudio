from __future__ import annotations

from typing import Any

from novel_app.schemas import PublishPackage
from novel_app.state import NovelState


def release_prepare(state: NovelState, runtime: Any = None) -> dict:
    card = state.get("current_card") or {}
    draft = state.get("current_draft") or {}
    chapter_no = card.get("chapter_no", 1)
    content = draft.get("content", "")
    package = PublishPackage(
        chapter_no=chapter_no,
        title=draft.get("title", f"第{chapter_no}章"),
        blurb=draft.get("summary_100w", ""),
        excerpt=content[:120],
    )
    return {
        "publish_package": package.model_dump(),
        "event_log": [f"release_package_ready:{chapter_no}"],
    }
