from __future__ import annotations

from typing import Literal

from .state import NovelState

MAX_REWRITES = 3

RouteName = Literal["release_prepare", "patch_writer", "chapter_planner", "human_gate"]


def route_after_review(state: NovelState) -> RouteName:
    decision = (state.get("phase_decision") or {}).get("final_decision", "human_check")

    # 重写超过上限，强制转人工
    if decision == "rewrite" and state.get("rewrite_count", 0) >= MAX_REWRITES:
        return "human_gate"

    mapping: dict[str, RouteName] = {
        "pass": "release_prepare",
        "rewrite": "patch_writer",
        "replan": "chapter_planner",
        "human_check": "human_gate",
    }
    return mapping.get(decision, "human_gate")


FeedbackRouteName = Literal["chapter_planner", "__end__"]


def route_after_feedback(state: NovelState) -> FeedbackRouteName:
    target = state.get("target_chapters", 1)
    completed = state.get("chapters_completed", 0)
    if completed < target:
        return "chapter_planner"
    return "__end__"
