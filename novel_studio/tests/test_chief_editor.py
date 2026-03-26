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
