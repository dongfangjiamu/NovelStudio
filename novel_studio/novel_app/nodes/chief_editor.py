from __future__ import annotations

from hashlib import sha1
from typing import Any

from novel_app.schemas import PhaseDecision
from novel_app.state import NovelState


def _latest_reports(state: NovelState) -> list[dict]:
    reports = state.get("review_reports") or []
    latest: dict[str, dict] = {}
    for report in reports:
        latest[report["reviewer"]] = report
    return list(latest.values())


def _normalize_issue(reviewer: str, issue: dict, chapter_no: int | None) -> dict:
    issue_type = str(issue.get("type", "general")).strip() or "general"
    fix_instruction = str(issue.get("fix_instruction", "")).strip()
    evidence = str(issue.get("evidence", "")).strip()
    raw_key = "|".join([str(chapter_no or 0), reviewer, issue_type, fix_instruction or evidence])
    issue_id = f"iss_{sha1(raw_key.encode('utf-8')).hexdigest()[:10]}"
    return {
        "issue_id": issue_id,
        "chapter_no": chapter_no,
        "reviewer": reviewer,
        "severity": issue.get("severity", "minor"),
        "category": issue_type,
        "evidence": evidence,
        "fix_instruction": fix_instruction,
        "status": "open",
    }


def _build_issue_ledger(state: NovelState, reports: list[dict], *, chapter_no: int | None) -> dict:
    issues = []
    for report in reports:
        reviewer = report.get("reviewer", "unknown")
        for issue in report.get("issues", []):
            issues.append(_normalize_issue(reviewer, issue, chapter_no))

    open_issues = [item for item in issues if item["status"] == "open"]
    return {
        "chapter_no": chapter_no,
        "status": "needs_revision" if open_issues else "cleared",
        "open_count": len(open_issues),
        "resolved_count": 0,
        "issues": issues,
    }


def chief_editor(state: NovelState, runtime: Any = None) -> dict:
    del runtime
    reports = _latest_reports(state)
    chapter_no = ((state.get("current_card") or {}).get("chapter_no")) or ((state.get("publish_package") or {}).get("chapter_no"))
    if len(reports) < 4:
        decision = PhaseDecision(
            final_decision="human_check",
            must_fix=["审校报告不完整"],
            can_defer=[],
            next_owner="human_gate",
            reason="需要人工确认审校汇总是否正常。",
        )
        return {
            "phase_decision": decision.model_dump(),
            "issue_ledger": {
                "chapter_no": chapter_no,
                "status": "needs_human_review",
                "open_count": 1,
                "resolved_count": 0,
                "issues": [
                    {
                        "issue_id": "iss_missing_reports",
                        "chapter_no": chapter_no,
                        "reviewer": "chief_editor",
                        "severity": "major",
                        "category": "review_integrity",
                        "evidence": "审校报告数量不足，无法可靠汇总。",
                        "fix_instruction": "补齐缺失审校报告或转人工确认。",
                        "status": "open",
                    }
                ],
            },
        }

    human_review_requests = [report["reviewer"] for report in reports if report.get("decision") == "human_review"]
    if human_review_requests:
        decision = PhaseDecision(
            final_decision="human_check",
            must_fix=[],
            can_defer=[],
            next_owner="human_gate",
            reason=f"审校要求人工确认：{', '.join(human_review_requests)}",
        )
        return {
            "phase_decision": decision.model_dump(),
            "issue_ledger": {
                "chapter_no": chapter_no,
                "status": "needs_human_review",
                "open_count": len(human_review_requests),
                "resolved_count": 0,
                "issues": [
                    {
                        "issue_id": f"iss_human_{reviewer}",
                        "chapter_no": chapter_no,
                        "reviewer": reviewer,
                        "severity": "major",
                        "category": "human_review",
                        "evidence": f"{reviewer} 审校要求人工确认。",
                        "fix_instruction": "由人工确认后决定继续、重写或重规划。",
                        "status": "open",
                    }
                    for reviewer in human_review_requests
                ],
            },
            "event_log": ["phase_decision:human_check"],
        }

    hard_violations = [v for report in reports for v in report.get("hard_violations", [])]
    if hard_violations:
        decision = PhaseDecision(
            final_decision="replan",
            must_fix=hard_violations,
            can_defer=[],
            next_owner="chapter_planner",
            reason="存在硬违规，需要回到章卡层重新规划。",
        )
        return {
            "phase_decision": decision.model_dump(),
            "issue_ledger": {
                "chapter_no": chapter_no,
                "status": "needs_replan",
                "open_count": len(hard_violations),
                "resolved_count": 0,
                "issues": [
                    {
                        "issue_id": f"iss_hard_{index + 1}",
                        "chapter_no": chapter_no,
                        "reviewer": "chief_editor",
                        "severity": "critical",
                        "category": "hard_violation",
                        "evidence": violation,
                        "fix_instruction": violation,
                        "status": "open",
                    }
                    for index, violation in enumerate(hard_violations)
                ],
            },
        }

    must_fix = [
        issue["fix_instruction"]
        for report in reports
        for issue in report.get("issues", [])
        if issue.get("severity") in {"critical", "major"}
    ]
    can_defer = [
        issue["fix_instruction"]
        for report in reports
        for issue in report.get("issues", [])
        if issue.get("severity") == "minor"
    ]

    final_decision = "rewrite" if must_fix else "pass"
    next_owner = "patch_writer" if must_fix else "release_prepare"
    reason = "存在需要修补的主要问题。" if must_fix else "通过当前阶段，可以进入发布与 Canon 回写。"

    decision = PhaseDecision(
        final_decision=final_decision,
        must_fix=must_fix,
        can_defer=can_defer,
        next_owner=next_owner,
        reason=reason,
    )
    issue_ledger = _build_issue_ledger(state, reports, chapter_no=chapter_no)
    return {
        "phase_decision": decision.model_dump(),
        "issue_ledger": issue_ledger,
        "event_log": [f"phase_decision:{final_decision}"],
    }
