from novel_app.nodes import writer


def test_draft_writer_passes_learning_guardrails_to_llm(monkeypatch) -> None:
    monkeypatch.setenv("NOVEL_STUDIO_STUB_MODE", "false")
    captured: dict[str, object] = {}

    def fake_invoke_structured(**kwargs):
        captured.update(kwargs)
        return {
            "title": "第2章 初稿",
            "summary_100w": "初稿摘要",
            "content": "正文",
            "canon_delta_candidate": {
                "character_updates": [],
                "world_updates": [],
                "loop_updates": [],
            },
            "risk_notes": [],
        }

    monkeypatch.setattr(writer, "invoke_structured", fake_invoke_structured)

    result = writer.draft_writer(
        {
            "creative_contract": {"project": {"working_title": "测试"}},
            "story_bible": {"premise": "测试"},
            "canon_state": {"story_clock": {"current_chapter": 1}},
            "current_card": {
                "chapter_no": 2,
                "must_include": ["一个明确的微爽点"],
                "must_not_change": ["主角尚未知道幕后高层身份"],
            },
            "writer_playbook": {"always_apply": ["主角主动性前置"]},
            "chapter_lesson": {"carry_forward_rules": ["章末必须升级风险"]},
            "issue_ledger": {
                "issues": [
                    {
                        "issue_id": "iss_1",
                        "reviewer": "continuity",
                        "severity": "major",
                        "category": "canon",
                        "attempts": 2,
                        "fix_instruction": "提前埋下执事异常反应的可验证细节。",
                        "evidence": "主角判断依据还不够硬。",
                        "status": "recurring",
                    }
                ]
            },
        }
    )

    assert captured["prompt_name"] == "writer"
    assert captured["payload"]["pending_issues_summary"][0]["issue_id"] == "iss_1"
    assert "主角主动性前置" in captured["payload"]["draft_guardrails"]
    assert "章末必须升级风险" in captured["payload"]["draft_guardrails"]
    assert any("本章必须出现" in item for item in captured["payload"]["draft_guardrails"])
    assert any("优先规避顽固问题" in item for item in captured["payload"]["draft_guardrails"])
    assert result["drafting_context"]["addressed_issue_ids"] == ["iss_1"]
    assert result["drafting_context"]["stubborn_issue_ids"] == ["iss_1"]
    assert result["drafting_context"]["issue_applications"][0]["issue_id"] == "iss_1"
    assert result["drafting_context"]["guardrail_sources"][-1]["source_type"] == "pending_issue"
    assert result["event_log"] == ["chapter_draft_ready"]


def test_patch_writer_passes_issue_ledger_to_llm(monkeypatch) -> None:
    monkeypatch.setenv("NOVEL_STUDIO_STUB_MODE", "false")
    captured: dict[str, object] = {}

    def fake_invoke_structured(**kwargs):
        captured.update(kwargs)
        return {
            "title": "第1章 修订稿",
            "summary_100w": "修订后摘要",
            "content": "修订后正文",
            "canon_delta_candidate": {
                "character_updates": [],
                "world_updates": [],
                "loop_updates": [],
            },
            "risk_notes": [],
        }

    monkeypatch.setattr(writer, "invoke_structured", fake_invoke_structured)

    result = writer.patch_writer(
        {
            "creative_contract": {"project": {"working_title": "测试"}},
            "story_bible": {"premise": "测试"},
            "canon_state": {"story_clock": {"current_chapter": 1}},
            "current_card": {"chapter_no": 1},
            "current_draft": {"title": "第1章", "content": "原稿"},
            "phase_decision": {"final_decision": "rewrite"},
            "issue_ledger": {"chapter_no": 1, "issues": [{"issue_id": "iss_1", "fix_instruction": "补强试探动作"}]},
            "review_reports": [],
        }
    )

    assert captured["prompt_name"] == "patch_writer"
    assert captured["payload"]["issue_ledger"]["issues"][0]["issue_id"] == "iss_1"
    assert result["rewrite_count"] == 1
