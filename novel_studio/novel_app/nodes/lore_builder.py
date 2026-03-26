from __future__ import annotations

from typing import Any

from novel_app.schemas import StoryBible
from novel_app.state import NovelState
from novel_app.utils.llm import invoke_structured


def _stub_bible(state: NovelState) -> StoryBible:
    contract = state.get("creative_contract") or {}
    hook = ((contract.get("reader_promise") or {}).get("one_sentence_hook")) or "一段危险的秘密将撬动世界"
    return StoryBible(
        premise=hook,
        world_rules=[
            "每次越阶获益都必须付出明确代价。",
            "宗门制度允许压迫弱者，但不能无缘无故撕裂内部秩序。",
            "公开力量体系与隐藏真相之间始终保持张力。",
        ],
        factions=["青岚宗", "北荒散修盟", "黑炉会"],
        character_cards=[
            {
                "character_id": "mc",
                "role": "protagonist",
                "desire": "活下去并查清自己被逐出师门的真相",
                "fear": "失去最后一点可依赖的身份与力量",
                "voiceprint": "克制、警惕、内心计算多于外露表达",
            },
            {
                "character_id": "mentor",
                "role": "ambiguous_guide",
                "desire": "借主角撬开禁地旧案",
                "fear": "自己真实身份暴露",
                "voiceprint": "温和却始终留有空白",
            },
        ],
        fixed_terms=["外门", "内门", "禁地炉火", "炼气三层"],
        red_lines=["不能出现无代价外挂", "不能突然洗白核心反派"],
    )


def lore_builder(state: NovelState, runtime: Any = None) -> dict:
    existing = state.get("story_bible")
    if existing:
        return {
            "story_bible": existing,
            "event_log": ["story_bible_reused"],
        }

    payload = {"creative_contract": state.get("creative_contract", {})}
    runtime_context = getattr(runtime, "context", None)
    bible = invoke_structured(
        prompt_name="lore_builder",
        schema_cls=StoryBible,
        payload=payload,
        runtime_context=runtime_context,
        stub_factory=lambda: _stub_bible(state),
    )
    return {
        "story_bible": bible,
        "event_log": ["story_bible_ready"],
    }
