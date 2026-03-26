from novel_app.nodes.chief_editor import chief_editor


def test_chief_editor_requests_rewrite_when_major_issues_exist() -> None:
    state = {
        "review_reports": [
            {
                "reviewer": "continuity",
                "decision": "rewrite",
                "scores": {"continuity": 78, "pacing": 80, "style": 80, "hook": 79, "total": 79},
                "hard_violations": [],
                "issues": [
                    {
                        "severity": "major",
                        "type": "canon",
                        "evidence": "test",
                        "fix_instruction": "补一个执事反应。",
                    }
                ],
            },
            {
                "reviewer": "pacing",
                "decision": "rewrite",
                "scores": {"continuity": 84, "pacing": 76, "style": 81, "hook": 80, "total": 78},
                "hard_violations": [],
                "issues": [
                    {
                        "severity": "major",
                        "type": "pacing",
                        "evidence": "test",
                        "fix_instruction": "更早做试探。",
                    }
                ],
            },
            {
                "reviewer": "style",
                "decision": "pass",
                "scores": {"continuity": 82, "pacing": 82, "style": 82, "hook": 82, "total": 81},
                "hard_violations": [],
                "issues": [],
            },
            {
                "reviewer": "reader_sim",
                "decision": "rewrite",
                "scores": {"continuity": 82, "pacing": 84, "style": 80, "hook": 81, "total": 80},
                "hard_violations": [],
                "issues": [
                    {
                        "severity": "major",
                        "type": "hook",
                        "evidence": "test",
                        "fix_instruction": "把危险感再推高一点。",
                    }
                ],
            },
        ]
    }
    result = chief_editor(state)
    assert result["phase_decision"]["final_decision"] == "rewrite"
    assert result["phase_decision"]["next_owner"] == "patch_writer"
    assert result["issue_ledger"]["status"] == "needs_revision"
    assert result["issue_ledger"]["open_count"] == 3
    assert len(result["issue_ledger"]["issues"]) == 3
    assert all(item["status"] == "open" for item in result["issue_ledger"]["issues"])
    assert all(item["issue_id"].startswith("iss_") for item in result["issue_ledger"]["issues"])


def test_chief_editor_passes_when_no_major_issues_exist() -> None:
    state = {
        "review_reports": [
            {
                "reviewer": "continuity",
                "decision": "pass",
                "scores": {"continuity": 90, "pacing": 84, "style": 82, "hook": 84, "total": 85},
                "hard_violations": [],
                "issues": [],
            },
            {
                "reviewer": "pacing",
                "decision": "pass",
                "scores": {"continuity": 84, "pacing": 88, "style": 81, "hook": 86, "total": 85},
                "hard_violations": [],
                "issues": [],
            },
            {
                "reviewer": "style",
                "decision": "pass",
                "scores": {"continuity": 82, "pacing": 82, "style": 86, "hook": 82, "total": 83},
                "hard_violations": [],
                "issues": [],
            },
            {
                "reviewer": "reader_sim",
                "decision": "pass",
                "scores": {"continuity": 82, "pacing": 84, "style": 80, "hook": 90, "total": 84},
                "hard_violations": [],
                "issues": [],
            },
        ]
    }
    result = chief_editor(state)
    assert result["phase_decision"]["final_decision"] == "pass"
    assert result["phase_decision"]["next_owner"] == "release_prepare"
    assert result["issue_ledger"]["status"] == "cleared"
    assert result["issue_ledger"]["open_count"] == 0
    assert result["issue_ledger"]["resolved_count"] == 0


def test_chief_editor_marks_previous_open_issues_as_resolved() -> None:
    previous_issue = {
        "issue_id": "iss_old_1",
        "chapter_no": 1,
        "reviewer": "pacing",
        "severity": "major",
        "category": "pacing",
        "evidence": "主角主动试探来得偏晚。",
        "fix_instruction": "让主角更早做出一次带风险的小试探。",
        "status": "open",
        "attempts": 1,
    }
    state = {
        "issue_ledger": {
            "chapter_no": 1,
            "status": "needs_revision",
            "open_count": 1,
            "new_count": 1,
            "recurring_count": 0,
            "resolved_count": 0,
            "issues": [previous_issue],
        },
        "review_reports": [
            {
                "reviewer": "continuity",
                "decision": "pass",
                "scores": {"continuity": 90, "pacing": 84, "style": 82, "hook": 84, "total": 85},
                "hard_violations": [],
                "issues": [],
            },
            {
                "reviewer": "pacing",
                "decision": "pass",
                "scores": {"continuity": 84, "pacing": 88, "style": 81, "hook": 86, "total": 85},
                "hard_violations": [],
                "issues": [],
            },
            {
                "reviewer": "style",
                "decision": "pass",
                "scores": {"continuity": 82, "pacing": 82, "style": 86, "hook": 82, "total": 83},
                "hard_violations": [],
                "issues": [],
            },
            {
                "reviewer": "reader_sim",
                "decision": "pass",
                "scores": {"continuity": 82, "pacing": 84, "style": 80, "hook": 90, "total": 84},
                "hard_violations": [],
                "issues": [],
            },
        ],
    }

    result = chief_editor(state)

    assert result["phase_decision"]["final_decision"] == "pass"
    assert result["issue_ledger"]["status"] == "cleared"
    assert result["issue_ledger"]["open_count"] == 0
    assert result["issue_ledger"]["resolved_count"] == 1
    assert result["issue_ledger"]["issues"][0]["issue_id"] == "iss_old_1"
    assert result["issue_ledger"]["issues"][0]["status"] == "resolved"


def test_chief_editor_marks_repeated_issue_as_recurring() -> None:
    previous_issue = {
        "issue_id": "iss_old_1",
        "chapter_no": 1,
        "reviewer": "pacing",
        "severity": "major",
        "category": "pacing",
        "evidence": "主角主动试探来得偏晚。",
        "fix_instruction": "让主角更早做出一次带风险的小试探。",
        "status": "open",
        "attempts": 1,
    }
    state = {
        "issue_ledger": {
            "chapter_no": 1,
            "status": "needs_revision",
            "open_count": 1,
            "new_count": 1,
            "recurring_count": 0,
            "resolved_count": 0,
            "issues": [previous_issue],
        },
        "review_reports": [
            {
                "reviewer": "continuity",
                "decision": "pass",
                "scores": {"continuity": 90, "pacing": 84, "style": 82, "hook": 84, "total": 85},
                "hard_violations": [],
                "issues": [],
            },
            {
                "reviewer": "pacing",
                "decision": "rewrite",
                "scores": {"continuity": 84, "pacing": 76, "style": 81, "hook": 80, "total": 78},
                "hard_violations": [],
                "issues": [
                    {
                        "severity": "major",
                        "type": "pacing",
                        "evidence": "主角主动试探来得偏晚。",
                        "fix_instruction": "让主角更早做出一次带风险的小试探。",
                    }
                ],
            },
            {
                "reviewer": "style",
                "decision": "pass",
                "scores": {"continuity": 82, "pacing": 82, "style": 86, "hook": 82, "total": 83},
                "hard_violations": [],
                "issues": [],
            },
            {
                "reviewer": "reader_sim",
                "decision": "pass",
                "scores": {"continuity": 82, "pacing": 84, "style": 80, "hook": 90, "total": 84},
                "hard_violations": [],
                "issues": [],
            },
        ],
    }

    result = chief_editor(state)

    assert result["phase_decision"]["final_decision"] == "rewrite"
    assert result["issue_ledger"]["open_count"] == 1
    assert result["issue_ledger"]["recurring_count"] == 1
    assert result["issue_ledger"]["new_count"] == 0
    assert result["issue_ledger"]["resolved_count"] == 0
    assert result["issue_ledger"]["issues"][0]["issue_id"] == "iss_old_1"
    assert result["issue_ledger"]["issues"][0]["status"] == "recurring"
    assert result["issue_ledger"]["issues"][0]["attempts"] == 2


def test_chief_editor_routes_to_human_check_when_reviewer_requests_it() -> None:
    state = {
        "review_reports": [
            {
                "reviewer": "continuity",
                "decision": "human_review",
                "scores": {"continuity": 65, "pacing": 70, "style": 80, "hook": 70, "total": 71},
                "hard_violations": [],
                "issues": [],
            },
            {
                "reviewer": "pacing",
                "decision": "pass",
                "scores": {"continuity": 82, "pacing": 82, "style": 82, "hook": 82, "total": 82},
                "hard_violations": [],
                "issues": [],
            },
            {
                "reviewer": "style",
                "decision": "pass",
                "scores": {"continuity": 82, "pacing": 82, "style": 82, "hook": 82, "total": 82},
                "hard_violations": [],
                "issues": [],
            },
            {
                "reviewer": "reader_sim",
                "decision": "pass",
                "scores": {"continuity": 82, "pacing": 82, "style": 82, "hook": 82, "total": 82},
                "hard_violations": [],
                "issues": [],
            },
        ]
    }

    result = chief_editor(state)

    assert result["phase_decision"]["final_decision"] == "human_check"
    assert result["phase_decision"]["next_owner"] == "human_gate"
    assert result["issue_ledger"]["status"] == "needs_human_review"
