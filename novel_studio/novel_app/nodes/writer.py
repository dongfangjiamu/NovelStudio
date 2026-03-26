from __future__ import annotations

from typing import Any

from novel_app.schemas import ChapterDraft
from novel_app.state import NovelState
from novel_app.utils.llm import invoke_structured, stub_mode_enabled


def _draft_stub(state: NovelState) -> ChapterDraft:
    card = state.get("current_card") or {}
    chapter_no = card.get("chapter_no", 1)
    hook = ((card.get("hook") or {}).get("chapter_end_question")) or "下一章会发生什么？"
    content = (
        f"第{chapter_no}章，主角拖着受罚后的身体离开惩戒场。\n\n"
        "他原本只想低头熬过今天，却在经过禁地外围时，听见炉火里传来两个人的对话。"
        "第一道声音苍老而缓慢，像是被火烤干的木头；第二道声音更轻，却精准说出了‘旧案’两个字。"
        "主角立刻意识到，这场看似针对他的惩戒，可能牵连着更深的东西。\n\n"
        "他压住回头的冲动，装作体力不支，借着旁人讥笑掩饰自己的停顿。"
        "就在执事准备再次羞辱他时，主角顺手借势把对方先前克扣外门配药的事点破，令场面短暂失控。"
        "这给了他一个小小的翻盘点，也让他确认执事在听到‘旧案’后神色明显变了。\n\n"
        f"章末，主角望向禁地方向，第一次认真怀疑：{hook}"
    )
    return ChapterDraft(
        title=f"第{chapter_no}章 炉火中的第二道声音",
        summary_100w="主角在受罚后偶然听见禁地炉火中的异常对话，意识到自己的遭遇可能牵连旧案，并通过一个小反击试探出执事确有异样。",
        content=content,
        canon_delta_candidate={
            "character_updates": [
                {"character_id": "mc", "known_facts_add": ["执事听到‘旧案’后神色异常"]}
            ],
            "world_updates": [{"type": "hint", "value": "禁地炉火可能与旧案相关"}],
            "loop_updates": [{"id": f"hook_{chapter_no}", "status": "active"}],
        },
        risk_notes=["当前版本偏稳，情绪强度还可以再上调。"],
    )


def _patch_stub(state: NovelState) -> ChapterDraft:
    current = state.get("current_draft") or {}
    patched_content = (current.get("content") or "") + "\n\n[PATCHED] 已补足主角迟疑与执事异常反应的因果链。"
    return ChapterDraft(
        title=current.get("title", "修订稿"),
        summary_100w=current.get("summary_100w", "") + "（修订版）",
        content=patched_content,
        canon_delta_candidate=current.get("canon_delta_candidate", {"character_updates": [], "world_updates": [], "loop_updates": []}),
        risk_notes=["已按问题单修补主要节奏与动机问题。"],
    )


def draft_writer(state: NovelState, runtime: Any = None) -> dict:
    payload = {
        "creative_contract": state.get("creative_contract", {}),
        "story_bible": state.get("story_bible", {}),
        "canon_state": state.get("canon_state", {}),
        "current_card": state.get("current_card", {}),
        "writer_playbook": state.get("writer_playbook", {}),
        "latest_chapter_lesson": state.get("chapter_lesson", {}),
        "human_instruction": state.get("human_instruction", {}),
    }
    runtime_context = getattr(runtime, "context", None)
    draft = invoke_structured(
        prompt_name="writer",
        schema_cls=ChapterDraft,
        payload=payload,
        runtime_context=runtime_context,
        stub_factory=lambda: _draft_stub(state),
    )
    return {
        "current_draft": draft,
        "event_log": ["chapter_draft_ready"],
    }


def patch_writer(state: NovelState, runtime: Any = None) -> dict:
    if stub_mode_enabled():
        draft = _patch_stub(state).model_dump()
    else:
        payload = {
            "creative_contract": state.get("creative_contract", {}),
            "story_bible": state.get("story_bible", {}),
            "canon_state": state.get("canon_state", {}),
            "current_card": state.get("current_card", {}),
            "current_draft": state.get("current_draft", {}),
            "phase_decision": state.get("phase_decision", {}),
            "review_reports": state.get("review_reports", []),
            "writer_playbook": state.get("writer_playbook", {}),
            "latest_chapter_lesson": state.get("chapter_lesson", {}),
            "human_instruction": state.get("human_instruction", {}),
        }
        runtime_context = getattr(runtime, "context", None)
        draft = invoke_structured(
            prompt_name="patch_writer",
            schema_cls=ChapterDraft,
            payload=payload,
            runtime_context=runtime_context,
            stub_factory=lambda: _patch_stub(state),
        )
    return {
        "current_draft": draft,
        "rewrite_count": state.get("rewrite_count", 0) + 1,
        "event_log": ["chapter_draft_patched"],
    }
