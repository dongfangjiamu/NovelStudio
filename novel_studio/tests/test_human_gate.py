from novel_app.nodes.human_gate import human_gate


def test_human_gate_returns_actionable_guidance() -> None:
    result = human_gate(
        {
            "current_card": {"chapter_no": 3},
            "phase_decision": {
                "reason": "需要人工判断是否继续当前章。",
                "must_fix": ["补足执事异常反应"],
                "can_defer": ["文风可后调"],
            },
            "review_reports": [
                {"reviewer": "continuity", "decision": "human_review"},
                {"reviewer": "style", "decision": "pass"},
            ],
            "issue_ledger": {
                "progress_summary": "有 1 个关键问题连续未关闭，建议人工介入。",
                "issues": [
                    {
                        "issue_id": "iss_stubborn_1",
                        "reviewer": "continuity",
                        "severity": "major",
                        "attempts": 2,
                        "fix_instruction": "补足执事异常反应",
                        "evidence": "证据链仍不够",
                        "status": "recurring",
                    }
                ],
            },
            "human_instruction": {"comment": "保留悬念，但补强证据链"},
        }
    )

    assert result["blockers"] == ["需要人工审核或继续指令。"]
    assert result["human_guidance"]["chapter_no"] == 3
    assert result["human_guidance"]["must_fix"] == ["补足执事异常反应"]
    assert result["human_guidance"]["reviewer_decisions"]["continuity"] == "human_review"
    assert result["human_guidance"]["issue_progress_summary"] == "有 1 个关键问题连续未关闭，建议人工介入。"
    assert result["human_guidance"]["stubborn_issues"][0]["issue_id"] == "iss_stubborn_1"
    assert result["human_guidance"]["stubborn_issues"][0]["attempts"] == 2
    assert result["event_log"] == ["human_gate_reached", "human_instruction_received"]
