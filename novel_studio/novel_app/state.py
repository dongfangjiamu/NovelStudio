from __future__ import annotations

from dataclasses import dataclass
from operator import add
from typing import Annotated

from typing_extensions import TypedDict


def merge_review_reports(left: list[dict] | None, right: list[dict] | None) -> list[dict]:
    merged: dict[str, dict] = {}
    for item in (left or []) + (right or []):
        reviewer = item.get("reviewer", f"anonymous_{len(merged)}")
        merged[reviewer] = item
    return list(merged.values())


class InputState(TypedDict, total=False):
    user_brief: dict
    target_chapters: int


class OutputState(TypedDict, total=False):
    phase_decision: dict
    publish_package: dict
    canon_state: dict
    feedback_summary: dict
    event_log: list[str]


class NovelState(TypedDict, total=False):
    user_brief: dict
    creative_contract: dict
    story_bible: dict
    arc_plan: dict
    canon_state: dict
    current_card: dict
    current_draft: dict
    phase_decision: dict
    publish_package: dict
    feedback_summary: dict
    review_reports: Annotated[list[dict], merge_review_reports]
    blockers: Annotated[list[str], add]
    event_log: Annotated[list[str], add]
    rewrite_count: int
    target_chapters: int
    chapters_completed: int


@dataclass
class RuntimeContext:
    project_id: str
    operator_id: str
    model_name: str = "gpt-5-nano"
    model_provider: str = "openai"
