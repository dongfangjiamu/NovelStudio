from __future__ import annotations

from typing import Any

from novel_app.schemas import PublishPackage
from novel_app.state import NovelState


def _word_count(text: str) -> int:
    return len(text.replace("\n", "").replace(" ", ""))


def _reviewer_summary(state: NovelState) -> dict[str, Any]:
    reports = state.get("review_reports") or []
    reviewer_decisions = {
        report.get("reviewer", f"reviewer_{idx}"): report.get("decision", "unknown")
        for idx, report in enumerate(reports)
    }
    major_count = sum(
        1
        for report in reports
        for issue in report.get("issues", [])
        if issue.get("severity") in {"critical", "major"}
    )
    minor_count = sum(
        1
        for report in reports
        for issue in report.get("issues", [])
        if issue.get("severity") == "minor"
    )
    return {
        "final_decision": (state.get("phase_decision") or {}).get("final_decision"),
        "reviewer_decisions": reviewer_decisions,
        "major_issue_count": major_count,
        "minor_issue_count": minor_count,
    }


def _canon_snapshot(state: NovelState) -> dict[str, Any]:
    canon = state.get("canon_state") or {}
    story_clock = canon.get("story_clock") or {}
    open_loops = canon.get("open_loops") or []
    return {
        "story_clock": story_clock,
        "open_loop_ids": [
            item.get("id", f"loop_{idx}") if isinstance(item, dict) else str(item)
            for idx, item in enumerate(open_loops)
        ],
        "last_chapter_summary": canon.get("last_chapter_summary"),
    }


def release_prepare(state: NovelState, runtime: Any = None) -> dict:
    del runtime

    card = state.get("current_card") or {}
    draft = state.get("current_draft") or {}
    chapter_no = card.get("chapter_no", 1)
    content = draft.get("content", "")
    package = PublishPackage(
        chapter_no=chapter_no,
        title=draft.get("title", f"第{chapter_no}章"),
        blurb=draft.get("summary_100w", ""),
        excerpt=content[:120],
        full_text=content,
        word_count=_word_count(content),
        chapter_end_question=((card.get("hook") or {}).get("chapter_end_question")) or "",
        reviewer_summary=_reviewer_summary(state),
        canon_snapshot=_canon_snapshot(state),
        operator_notes=((state.get("human_instruction") or {}).get("comment")),
    )
    return {
        "publish_package": package.model_dump(),
        "event_log": [f"release_package_ready:{chapter_no}"],
    }
