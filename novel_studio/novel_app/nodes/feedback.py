from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from novel_app.state import NovelState


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = str(item or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _review_issues(state: NovelState) -> list[dict[str, Any]]:
    reports = state.get("review_reports") or []
    issues: list[dict[str, Any]] = []
    for report in reports:
        for issue in report.get("issues", []):
            issues.append(
                {
                    "reviewer": report.get("reviewer", "unknown"),
                    "severity": issue.get("severity", "minor"),
                    "type": issue.get("type", "general"),
                    "evidence": str(issue.get("evidence", "")).strip(),
                    "fix_instruction": str(issue.get("fix_instruction", "")).strip(),
                }
            )
    return issues


def _human_rules(state: NovelState) -> list[str]:
    instruction = state.get("human_instruction") or {}
    values: list[str] = []
    comment = str(instruction.get("comment", "")).strip()
    reason = str(instruction.get("reason", "")).strip()
    requested_action = str(instruction.get("requested_action", "")).strip()
    if comment:
        values.append(comment)
    if reason:
        values.append(f"优先满足人工意图：{reason}")
    if requested_action and requested_action not in {"continue", "rewrite", "replan", "human_check", "quick_trial"}:
        values.append(f"遵循人工动作：{requested_action}")
    payload = instruction.get("payload") or {}
    if isinstance(payload, dict):
        for key, value in payload.items():
            normalized = str(value).strip()
            if normalized and len(normalized) <= 120:
                values.append(f"{key}: {normalized}")
    return _dedupe_preserve_order(values)


def _build_chapter_lesson(state: NovelState, chapter_no: int) -> dict[str, Any]:
    publish_package = state.get("publish_package") or {}
    current_card = state.get("current_card") or {}
    issue_ledger = state.get("issue_ledger") or {}
    issues = list(issue_ledger.get("issues") or []) or _review_issues(state)
    rewrite_count = int(state.get("rewrite_count", 0) or 0)
    fix_rules = _dedupe_preserve_order([issue.get("fix_instruction", "") for issue in issues if issue.get("fix_instruction")])
    fail_reasons = _dedupe_preserve_order([issue.get("evidence", "") for issue in issues if issue.get("evidence")])
    pass_reasons = []
    if rewrite_count == 0:
        pass_reasons.append("首稿通过当前阶段审校，无需重写。")
    else:
        pass_reasons.append(f"经过 {rewrite_count} 轮修订后，主要问题已收敛并通过审校。")
    if publish_package.get("chapter_end_question"):
        pass_reasons.append("章末驱动已经明确落地，保留了继续阅读的牵引。")
    if current_card.get("purpose"):
        pass_reasons.append(f"本章核心目的已经实现：{current_card['purpose']}")

    discarded_patterns = []
    for issue in issues:
        issue_type = issue.get("category") or issue.get("type") or "general"
        if issue_type == "pacing":
            discarded_patterns.append("避免长时间铺垫后才进入主冲突。")
        elif issue_type == "hook":
            discarded_patterns.append("避免只提出问题而不升级风险。")
        elif issue_type == "canon":
            discarded_patterns.append("避免关键判断缺少可验证的行为证据。")
        elif issue["evidence"]:
            discarded_patterns.append(issue["evidence"])

    carry_forward_rules = _dedupe_preserve_order(
        fix_rules + _human_rules(state) + [
            "继续保持章节目的单一明确，不要在同一章同时展开过多新支线。",
            "继续保证章末存在明确的下一章驱动力。",
        ]
    )

    return {
        "chapter_no": chapter_no,
        "title": publish_package.get("title") or current_card.get("purpose") or f"第{chapter_no}章",
        "rewrite_count": rewrite_count,
        "issue_ledger_status": issue_ledger.get("status", "cleared"),
        "open_issue_count": int(issue_ledger.get("open_count", 0) or 0),
        "pass_reasons": _dedupe_preserve_order(pass_reasons),
        "fail_reasons": fail_reasons,
        "carry_forward_rules": carry_forward_rules,
        "discarded_patterns": _dedupe_preserve_order(discarded_patterns),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _merge_writer_playbook(state: NovelState, chapter_lesson: dict[str, Any], chapter_no: int) -> dict[str, Any]:
    existing = state.get("writer_playbook") or {}
    return {
        "version": int(existing.get("version", 0) or 0) + 1,
        "last_chapter_no": chapter_no,
        "always_apply": _dedupe_preserve_order(
            list(existing.get("always_apply", [])) + list(chapter_lesson.get("carry_forward_rules", []))
        )[:12],
        "watch_out": _dedupe_preserve_order(
            list(existing.get("watch_out", []))
            + list(chapter_lesson.get("fail_reasons", []))
            + list(chapter_lesson.get("discarded_patterns", []))
        )[:12],
        "validated_patterns": _dedupe_preserve_order(
            list(existing.get("validated_patterns", [])) + list(chapter_lesson.get("pass_reasons", []))
        )[:12],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def feedback_ingest(state: NovelState, runtime: Any = None) -> dict:
    del runtime
    chapter_no = ((state.get("current_card") or {}).get("chapter_no")) or 1
    chapter_lesson = _build_chapter_lesson(state, chapter_no)
    writer_playbook = _merge_writer_playbook(state, chapter_lesson, chapter_no)
    return {
        "feedback_summary": {
            "chapter_no": chapter_no,
            "immediate_actions": list(chapter_lesson.get("carry_forward_rules", []))[:3],
            "observe": list(chapter_lesson.get("pass_reasons", []))[:3],
            "discard": list(chapter_lesson.get("discarded_patterns", []))[:3],
            "playbook_version": writer_playbook["version"],
        },
        "chapter_lesson": chapter_lesson,
        "writer_playbook": writer_playbook,
        "latest_review_reports": list(state.get("review_reports", [])),
        "chapters_completed": state.get("chapters_completed", 0) + 1,
        "rewrite_count": 0,
        "review_reports": [],
        "event_log": [f"feedback_ingested:{chapter_no}"],
    }
