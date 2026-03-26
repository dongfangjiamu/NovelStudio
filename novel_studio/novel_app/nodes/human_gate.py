from __future__ import annotations

from typing import Any

from novel_app.state import NovelState


def human_gate(state: NovelState, runtime: Any = None) -> dict:
    phase_decision = state.get("phase_decision") or {}
    current_card = state.get("current_card") or {}
    reports = state.get("review_reports") or []
    human_instruction = state.get("human_instruction")
    issue_ledger = state.get("issue_ledger") or {}
    stubborn_issues = [
        {
            "issue_id": issue.get("issue_id"),
            "reviewer": issue.get("reviewer"),
            "severity": issue.get("severity"),
            "attempts": issue.get("attempts", 1),
            "fix_instruction": issue.get("fix_instruction"),
            "evidence": issue.get("evidence"),
        }
        for issue in issue_ledger.get("issues", [])
        if issue.get("status") == "recurring" and int(issue.get("attempts", 0) or 0) >= 2
    ]
    guidance = {
        "chapter_no": current_card.get("chapter_no"),
        "reason": phase_decision.get("reason") or "需要人工审核或继续指令。",
        "must_fix": phase_decision.get("must_fix", []),
        "can_defer": phase_decision.get("can_defer", []),
        "reviewer_decisions": {
            report.get("reviewer", f"reviewer_{idx}"): report.get("decision", "unknown")
            for idx, report in enumerate(reports)
        },
        "suggested_actions": ["continue", "rewrite", "replan"],
        "human_instruction": human_instruction,
        "issue_progress_summary": issue_ledger.get("progress_summary"),
        "stubborn_issues": stubborn_issues,
    }
    return {
        "blockers": ["需要人工审核或继续指令。"],
        "human_guidance": guidance,
        "event_log": ["human_gate_reached"] + (["human_instruction_received"] if human_instruction else []),
    }
