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


def _pending_issue_summary(state: NovelState) -> list[dict[str, Any]]:
    issue_ledger = state.get("issue_ledger") or {}
    issues = []
    for issue in issue_ledger.get("issues", []):
        if issue.get("status") not in {"open", "recurring"}:
            continue
        issues.append(
            {
                "issue_id": issue.get("issue_id"),
                "reviewer": issue.get("reviewer"),
                "severity": issue.get("severity"),
                "category": issue.get("category"),
                "attempts": issue.get("attempts", 1),
                "fix_instruction": issue.get("fix_instruction"),
                "evidence": issue.get("evidence"),
            }
        )
    return issues


def _planning_guardrails(state: NovelState) -> list[str]:
    writer_playbook = state.get("writer_playbook") or {}
    chapter_lesson = state.get("chapter_lesson") or {}
    pending_issues = _pending_issue_summary(state)

    guardrails: list[str] = []
    for item in writer_playbook.get("always_apply", [])[:6]:
        normalized = str(item).strip()
        if normalized:
            guardrails.append(normalized)
    for item in chapter_lesson.get("carry_forward_rules", [])[:4]:
        normalized = str(item).strip()
        if normalized:
            guardrails.append(normalized)
    for issue in pending_issues:
        fix_instruction = str(issue.get("fix_instruction", "")).strip()
        if not fix_instruction:
            continue
        if int(issue.get("attempts", 1) or 1) >= 2:
            guardrails.append(f"优先从章卡层规避顽固问题：{fix_instruction}")
        else:
            guardrails.append(f"提前规避已知问题：{fix_instruction}")

    deduped: list[str] = []
    seen: set[str] = set()
    for item in guardrails:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped[:10]


def _planning_evidence(state: NovelState, pending_issues: list[dict[str, Any]], planning_guardrails: list[str]) -> dict:
    writer_playbook = state.get("writer_playbook") or {}
    chapter_lesson = state.get("chapter_lesson") or {}
    playbook_rules = [str(item).strip() for item in writer_playbook.get("always_apply", [])[:6] if str(item).strip()]
    lesson_rules = [str(item).strip() for item in chapter_lesson.get("carry_forward_rules", [])[:4] if str(item).strip()]
    source_links = [
        {"guardrail": item, "source_type": "playbook", "source_ref": "always_apply"}
        for item in playbook_rules
    ]
    source_links.extend(
        {"guardrail": item, "source_type": "lesson", "source_ref": "carry_forward_rules"}
        for item in lesson_rules
    )
    issue_applications = []
    for issue in pending_issues:
        fix_instruction = str(issue.get("fix_instruction", "")).strip()
        if not fix_instruction:
            continue
        attempts = int(issue.get("attempts", 1) or 1)
        applied_guardrail = (
            f"优先从章卡层规避顽固问题：{fix_instruction}"
            if attempts >= 2
            else f"提前规避已知问题：{fix_instruction}"
        )
        issue_applications.append(
            {
                "issue_id": issue.get("issue_id"),
                "reviewer": issue.get("reviewer"),
                "attempts": attempts,
                "applied_guardrail": applied_guardrail,
                "fix_instruction": fix_instruction,
            }
        )
        source_links.append(
            {
                "guardrail": applied_guardrail,
                "source_type": "pending_issue",
                "source_ref": issue.get("issue_id"),
            }
        )
    return {
        "applied_guardrails": planning_guardrails,
        "guardrail_sources": source_links,
        "issue_applications": issue_applications,
    }


def chapter_planner(state: NovelState, runtime: Any = None) -> dict:
    pending_issues = _pending_issue_summary(state)
    planning_guardrails = _planning_guardrails(state)
    planning_evidence = _planning_evidence(state, pending_issues, planning_guardrails)
    payload = {
        "creative_contract": state.get("creative_contract", {}),
        "story_bible": state.get("story_bible", {}),
        "arc_plan": state.get("arc_plan", {}),
        "canon_state": state.get("canon_state", {}),
        "writer_playbook": state.get("writer_playbook", {}),
        "latest_chapter_lesson": state.get("chapter_lesson", {}),
        "issue_ledger": state.get("issue_ledger", {}),
        "pending_issues_summary": pending_issues,
        "planning_guardrails": planning_guardrails,
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
        "planning_context": {
            "chapter_no": card.get("chapter_no") if isinstance(card, dict) else None,
            **planning_evidence,
            "addressed_issue_ids": [item.get("issue_id") for item in pending_issues if item.get("issue_id")],
            "stubborn_issue_ids": [
                item.get("issue_id")
                for item in pending_issues
                if int(item.get("attempts", 1) or 1) >= 2 and item.get("issue_id")
            ],
            "source_counts": {
                "playbook_rules": len((state.get("writer_playbook") or {}).get("always_apply", [])),
                "lesson_rules": len((state.get("chapter_lesson") or {}).get("carry_forward_rules", [])),
                "pending_issues": len(pending_issues),
            },
        },
        "current_card": card,
        "event_log": [f"chapter_card_ready:{card['chapter_no']}"] if isinstance(card, dict) else ["chapter_card_ready"],
    }
