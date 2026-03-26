from __future__ import annotations

from typing import Any

from novel_app.schemas import ChapterCard
from novel_app.state import NovelState
from novel_app.utils.llm import invoke_structured


def _stub_card(state: NovelState) -> ChapterCard:
    canon = state.get("canon_state") or {}
    current_chapter = (((canon.get("story_clock") or {}).get("current_chapter")) or 0) + 1
    return ChapterCard(
        chapter_no=current_chapter,
        purpose="让主角第一次意识到受罚并不只是针对他个人，而是与被压住的旧案有关。",
        pov="third_limited_mc",
        entry_state={
            "required_context": ["主角刚结束体罚", "禁地炉火传出异样声响"],
            "emotional_state": "疲惫、戒备、压抑愤怒",
            "unresolved_threads": ["是谁推动了他的受罚", "导师是否知情"],
        },
        scene_beats=[
            {
                "goal": "主角想在不惹麻烦的情况下离开惩戒场",
                "conflict": "执事故意延长羞辱并诱导他失控",
                "turn": "炉火中的低语第一次点名提到‘旧案’",
            },
            {
                "goal": "主角试图确认自己是否听错",
                "conflict": "他必须在众目睽睽下掩饰异样，同时避免暴露对禁地的兴趣",
                "turn": "主角发现执事反应异常，确认这不是普通惩戒",
            },
        ],
        must_include=["一个明确的微爽点", "一个带风险的信息增量"],
        must_not_change=["主角仍是炼气三层", "主角尚未知道幕后高层身份"],
        hook={
            "chapter_end_question": "禁地炉火里第二个声音，到底是死人、器灵，还是某个活着的人？",
            "target_reader_impulse": "must_click_next",
        },
        word_count_target=3000,
    )


def chapter_planner(state: NovelState, runtime: Any = None) -> dict:
    payload = {
        "creative_contract": state.get("creative_contract", {}),
        "story_bible": state.get("story_bible", {}),
        "arc_plan": state.get("arc_plan", {}),
        "canon_state": state.get("canon_state", {}),
        "human_instruction": state.get("human_instruction", {}),
    }
    runtime_context = getattr(runtime, "context", None)
    card = invoke_structured(
        prompt_name="chapter_planner",
        schema_cls=ChapterCard,
        payload=payload,
        runtime_context=runtime_context,
        stub_factory=lambda: _stub_card(state),
    )
    return {
        "current_card": card,
        "event_log": [f"chapter_card_ready:{card['chapter_no']}"] if isinstance(card, dict) else ["chapter_card_ready"],
    }
