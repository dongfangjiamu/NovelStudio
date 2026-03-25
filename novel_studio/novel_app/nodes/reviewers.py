from __future__ import annotations

from typing import Any

from novel_app.schemas import ReviewIssue, ReviewReport, ReviewScores
from novel_app.state import NovelState


def _is_patched(state: NovelState) -> bool:
    draft = state.get("current_draft") or {}
    return "[PATCHED]" in (draft.get("content") or "")


def _make_report(reviewer: str, state: NovelState) -> ReviewReport:
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


def continuity_reviewer(state: NovelState, runtime: Any = None) -> dict:
    return {"review_reports": [_make_report("continuity", state).model_dump()]}


def pacing_reviewer(state: NovelState, runtime: Any = None) -> dict:
    return {"review_reports": [_make_report("pacing", state).model_dump()]}


def style_reviewer(state: NovelState, runtime: Any = None) -> dict:
    return {"review_reports": [_make_report("style", state).model_dump()]}


def reader_simulator(state: NovelState, runtime: Any = None) -> dict:
    return {"review_reports": [_make_report("reader_sim", state).model_dump()]}
