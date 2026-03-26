from __future__ import annotations

from typing import Any

from novel_app.schemas import ReviewIssue, ReviewReport, ReviewScores
from novel_app.state import NovelState
from novel_app.utils.llm import invoke_structured


REVIEWER_CONFIG = {
    "continuity": {
        "prompt_name": "continuity_reviewer",
        "review_focus": [
            "设定冲突",
            "时间线连续性",
            "角色已知/未知信息边界",
            "人设漂移",
            "因果链完整性",
        ],
    },
    "pacing": {
        "prompt_name": "pacing_reviewer",
        "review_focus": [
            "推进速度",
            "信息增量",
            "冲突密度",
            "场景切换效率",
            "章末钩子强度",
        ],
    },
    "style": {
        "prompt_name": "style_reviewer",
        "review_focus": [
            "叙事口吻一致性",
            "对白辨识度",
            "商业网文可读性",
            "句式拖沓与信息重复",
            "情绪表达是否到位",
        ],
    },
    "reader_sim": {
        "prompt_name": "reader_simulator",
        "review_focus": [
            "追读欲望",
            "付费点",
            "章末驱动力",
            "情绪回报",
            "是否有点击下一章的冲动",
        ],
    },
}


def _is_patched(state: NovelState) -> bool:
    draft = state.get("current_draft") or {}
    return "[PATCHED]" in (draft.get("content") or "")


def _stub_report(reviewer: str, state: NovelState) -> ReviewReport:
    patched = _is_patched(state)
    if reviewer == "continuity":
        return ReviewReport(
            reviewer="continuity",
            decision="pass" if patched else "rewrite",
            scores=ReviewScores(
                continuity=90 if patched else 78,
                pacing=84 if patched else 80,
                style=82 if patched else 80,
                hook=84 if patched else 79,
                total=85 if patched else 79,
            ),
            hard_violations=[],
            issues=[] if patched else [
                ReviewIssue(
                    severity="major",
                    type="canon",
                    evidence="主角对执事异常的判断还缺一个更明确的行为证据。",
                    fix_instruction="补一个执事听到‘旧案’后下意识停顿或改口的细节。",
                )
            ],
        )
    if reviewer == "pacing":
        return ReviewReport(
            reviewer="pacing",
            decision="pass" if patched else "rewrite",
            scores=ReviewScores(
                continuity=84,
                pacing=88 if patched else 76,
                style=81,
                hook=86 if patched else 80,
                total=85 if patched else 78,
            ),
            hard_violations=[],
            issues=[] if patched else [
                ReviewIssue(
                    severity="major",
                    type="pacing",
                    evidence="前半段信息释放较稳，但主角的试探动作来得稍晚。",
                    fix_instruction="让主角更早做出一次带风险的小试探。",
                )
            ],
        )
    if reviewer == "style":
        return ReviewReport(
            reviewer="style",
            decision="pass",
            scores=ReviewScores(
                continuity=82,
                pacing=82,
                style=86 if patched else 82,
                hook=82,
                total=83 if patched else 81,
            ),
            hard_violations=[],
            issues=[] if patched else [
                ReviewIssue(
                    severity="minor",
                    type="style",
                    evidence="情绪描写偏克制，商业爽感还可再推高一点。",
                    fix_instruction="在小反击处增加更鲜明的体感反馈。",
                )
            ],
        )
    return ReviewReport(
        reviewer="reader_sim",
        decision="pass" if patched else "rewrite",
        scores=ReviewScores(
            continuity=82,
            pacing=84,
            style=80,
            hook=90 if patched else 81,
            total=84 if patched else 80,
        ),
        hard_violations=[],
        issues=[] if patched else [
            ReviewIssue(
                severity="major",
                type="hook",
                evidence="章末问题足够明确，但上一段的悬念攀升还差半步。",
                fix_instruction="把主角的怀疑推到更危险的层级，再落到章末问句。",
            )
        ],
    )


def _review_payload(state: NovelState, reviewer: str) -> dict[str, Any]:
    config = REVIEWER_CONFIG[reviewer]
    issue_ledger = state.get("issue_ledger") or {}
    pending_issues = [
        {
            "issue_id": issue.get("issue_id"),
            "severity": issue.get("severity"),
            "category": issue.get("category"),
            "evidence": issue.get("evidence"),
            "fix_instruction": issue.get("fix_instruction"),
            "attempts": issue.get("attempts", 1),
        }
        for issue in issue_ledger.get("issues", [])
        if issue.get("reviewer") == reviewer and issue.get("status") in {"open", "recurring"}
    ]
    return {
        "reviewer": reviewer,
        "review_focus": config["review_focus"],
        "review_goal": "先核对待关闭旧问题是否已解决，再补充真正新的关键问题。",
        "pending_issues_for_reviewer": pending_issues,
        "creative_contract": state.get("creative_contract", {}),
        "story_bible": state.get("story_bible", {}),
        "arc_plan": state.get("arc_plan", {}),
        "canon_state": state.get("canon_state", {}),
        "current_card": state.get("current_card", {}),
        "current_draft": state.get("current_draft", {}),
    }


def _run_reviewer(state: NovelState, reviewer: str, runtime: Any = None) -> dict:
    config = REVIEWER_CONFIG[reviewer]
    runtime_context = getattr(runtime, "context", None)
    report = invoke_structured(
        prompt_name=config["prompt_name"],
        schema_cls=ReviewReport,
        payload=_review_payload(state, reviewer),
        runtime_context=runtime_context,
        stub_factory=lambda: _stub_report(reviewer, state),
    )
    return {
        "review_reports": [report],
        "event_log": [f"review_ready:{reviewer}:{report['decision']}"],
    }


def continuity_reviewer(state: NovelState, runtime: Any = None) -> dict:
    return _run_reviewer(state, "continuity", runtime)


def pacing_reviewer(state: NovelState, runtime: Any = None) -> dict:
    return _run_reviewer(state, "pacing", runtime)


def style_reviewer(state: NovelState, runtime: Any = None) -> dict:
    return _run_reviewer(state, "style", runtime)


def reader_simulator(state: NovelState, runtime: Any = None) -> dict:
    return _run_reviewer(state, "reader_sim", runtime)
