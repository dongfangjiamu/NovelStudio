from novel_app.nodes import chapter_planner


def test_chapter_planner_passes_learning_guardrails_to_llm(monkeypatch) -> None:
    monkeypatch.setenv("NOVEL_STUDIO_STUB_MODE", "false")
    captured: dict[str, object] = {}

    def fake_invoke_structured(**kwargs):
        captured.update(kwargs)
        return {
            "chapter_no": 2,
            "purpose": "让主角在不暴露自己的前提下再次验证执事异常",
            "pov": "third_limited_mc",
            "entry_state": {
                "required_context": ["第1章发现执事异常"],
                "emotional_state": "谨慎",
                "unresolved_threads": ["旧案与禁地的关系"],
            },
            "scene_beats": [
                {"goal": "确认异常", "conflict": "不能暴露", "turn": "得到新证据"},
                {"goal": "压住怀疑", "conflict": "执事反扑", "turn": "章末风险升级"},
            ],
            "must_include": ["微爽点"],
            "must_not_change": ["主角尚未知道幕后高层身份"],
            "hook": {
                "chapter_end_question": "主角是否要冒险潜入禁地？",
                "target_reader_impulse": "must_click_next",
            },
            "word_count_target": 2600,
        }

    monkeypatch.setattr(chapter_planner, "invoke_structured", fake_invoke_structured)

    result = chapter_planner.chapter_planner(
        {
            "creative_contract": {"project": {"working_title": "测试书"}},
            "story_bible": {"premise": "测试 premise"},
            "arc_plan": {"arc_name": "卷一"},
            "canon_state": {"story_clock": {"current_chapter": 1}},
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
            "human_instruction": {"comment": "保持主角主动性"},
        }
    )

    payload = captured["payload"]
    assert captured["prompt_name"] == "chapter_planner"
    assert payload["pending_issues_summary"][0]["issue_id"] == "iss_1"
    assert "主角主动性前置" in payload["planning_guardrails"]
    assert "章末必须升级风险" in payload["planning_guardrails"]
    assert any("顽固问题" in item for item in payload["planning_guardrails"])
    assert result["planning_context"]["addressed_issue_ids"] == ["iss_1"]
    assert result["planning_context"]["stubborn_issue_ids"] == ["iss_1"]
    assert result["planning_context"]["issue_applications"][0]["issue_id"] == "iss_1"
    assert result["planning_context"]["guardrail_sources"][-1]["source_type"] == "pending_issue"
    assert result["current_card"]["chapter_no"] == 2
    assert result["event_log"] == ["chapter_card_ready:2"]
