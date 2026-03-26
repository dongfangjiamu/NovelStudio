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


def _pending_issue_summary(state: NovelState) -> list[dict[str, Any]]:
    issue_ledger = state.get("issue_ledger") or {}
    return [
        {
            "issue_id": issue.get("issue_id"),
            "reviewer": issue.get("reviewer"),
            "severity": issue.get("severity"),
            "category": issue.get("category"),
            "attempts": issue.get("attempts", 1),
            "fix_instruction": issue.get("fix_instruction"),
            "evidence": issue.get("evidence"),
        }
        for issue in issue_ledger.get("issues", [])
        if issue.get("status") in {"open", "recurring"}
    ]


def _draft_guardrails(state: NovelState) -> list[str]:
    current_card = state.get("current_card") or {}
    writer_playbook = state.get("writer_playbook") or {}
    chapter_lesson = state.get("chapter_lesson") or {}
    pending_issues = _pending_issue_summary(state)

    values: list[str] = []
    for item in current_card.get("must_include", [])[:4]:
        normalized = str(item).strip()
        if normalized:
            values.append(f"本章必须出现：{normalized}")
    for item in current_card.get("must_not_change", [])[:4]:
        normalized = str(item).strip()
        if normalized:
            values.append(f"严禁改动：{normalized}")
    for item in writer_playbook.get("always_apply", [])[:6]:
        normalized = str(item).strip()
        if normalized:
            values.append(normalized)
    for item in chapter_lesson.get("carry_forward_rules", [])[:4]:
        normalized = str(item).strip()
        if normalized:
            values.append(normalized)
    for issue in pending_issues[:6]:
        fix_instruction = str(issue.get("fix_instruction", "")).strip()
        if not fix_instruction:
            continue
        prefix = "优先规避顽固问题" if int(issue.get("attempts", 1) or 1) >= 2 else "提前规避已知问题"
        values.append(f"{prefix}：{fix_instruction}")

    deduped: list[str] = []
    seen: set[str] = set()
    for item in values:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped[:12]


def draft_writer(state: NovelState, runtime: Any = None) -> dict:
    pending_issues = _pending_issue_summary(state)
    draft_guardrails = _draft_guardrails(state)
    payload = {
        "creative_contract": state.get("creative_contract", {}),
        "story_bible": state.get("story_bible", {}),
        "canon_state": state.get("canon_state", {}),
        "current_card": state.get("current_card", {}),
        "writer_playbook": state.get("writer_playbook", {}),
        "latest_chapter_lesson": state.get("chapter_lesson", {}),
        "issue_ledger": state.get("issue_ledger", {}),
        "pending_issues_summary": pending_issues,
        "draft_guardrails": draft_guardrails,
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
        "drafting_context": {
            "chapter_no": (state.get("current_card") or {}).get("chapter_no"),
            "applied_guardrails": draft_guardrails,
            "addressed_issue_ids": [item.get("issue_id") for item in pending_issues if item.get("issue_id")],
            "stubborn_issue_ids": [
                item.get("issue_id")
                for item in pending_issues
                if int(item.get("attempts", 1) or 1) >= 2 and item.get("issue_id")
            ],
            "must_include": list((state.get("current_card") or {}).get("must_include", []))[:4],
            "must_not_change": list((state.get("current_card") or {}).get("must_not_change", []))[:4],
        },
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
            "issue_ledger": state.get("issue_ledger", {}),
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
