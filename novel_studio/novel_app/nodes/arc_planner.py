from __future__ import annotations

from typing import Any

from novel_app.schemas import ArcPlan
from novel_app.state import NovelState
from novel_app.utils.llm import invoke_structured


def _stub_arc_plan(_: NovelState) -> ArcPlan:
    return ArcPlan(
        arc_name="卷一：炉火余烬",
        arc_goal="主角在外门生存压力中发现自己被逐出山门并非意外，并拿到第一份足以翻盘的证据。",
        conflict_core="主角既要保住身份与性命，又要在不暴露底牌的前提下接近禁地旧案。",
        milestones=[
            "第1章：主角在受罚中第一次听见禁地炉火中的异样对话。",
            "第2章：他意识到师门惩戒可能在针对某个被掩盖的旧案。",
            "第3章：主角被迫在保命和试探真相之间作出选择。",
        ],
        foreshadowing=["炉火中的第二个声音", "导师为何总在关键时刻缺席"],
        climax_hook="主角发现逐出师门的命令可能来自一位他从未见过的高层。",
    )


def arc_planner(state: NovelState, runtime: Any = None) -> dict:
    existing_plan = state.get("arc_plan")
    if existing_plan:
        return {
            "arc_plan": existing_plan,
            "canon_state": state.get("canon_state") or {
                "story_clock": {"current_arc": 1, "current_chapter": 0, "in_story_time": "day_0"},
                "character_states": {},
                "open_loops": [],
            },
            "event_log": ["arc_plan_reused"],
        }

    payload = {
        "creative_contract": state.get("creative_contract", {}),
        "story_bible": state.get("story_bible", {}),
    }
    runtime_context = getattr(runtime, "context", None)
    plan = invoke_structured(
        prompt_name="arc_planner",
        schema_cls=ArcPlan,
        payload=payload,
        runtime_context=runtime_context,
        stub_factory=lambda: _stub_arc_plan(state),
    )
    canon_state = state.get("canon_state") or {
        "story_clock": {"current_arc": 1, "current_chapter": 0, "in_story_time": "day_0"},
        "character_states": {
            "mc": {
                "location": "青岚宗外门",
                "injuries": [],
                "inventory": ["破旧弟子牌"],
                "known_facts": [],
                "hidden_from_mc": ["逐出师门另有幕后推动者"],
                "active_goals": ["活下去", "查清逐出真相"],
                "relationship_delta": [],
            }
        },
        "open_loops": [],
    }
    return {
        "arc_plan": plan,
        "canon_state": canon_state,
        "event_log": ["arc_plan_ready"],
    }
