from __future__ import annotations

from typing import Any

from novel_app.schemas import PhaseDecision
from novel_app.state import NovelState


def _latest_reports(state: NovelState) -> list[dict]:
    reports = state.get("review_reports") or []
    latest: dict[str, dict] = {}
    for report in reports:
        latest[report["reviewer"]] = report
    return list(latest.values())


def chief_editor(state: NovelState, runtime: Any = None) -> dict:
    reports = _latest_reports(state)
    if len(reports) < 4:
        decision = PhaseDecision(
            final_decision="human_check",
            must_fix=["审校报告不完整"],
            can_defer=[],
            next_owner="human_gate",
            reason="需要人工确认审校汇总是否正常。",
        )
        return {"phase_decision": decision.model_dump()}

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
        return {"phase_decision": decision.model_dump()}

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
    return {
        "phase_decision": decision.model_dump(),
        "event_log": [f"phase_decision:{final_decision}"],
    }
