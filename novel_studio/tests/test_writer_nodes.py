from novel_app.nodes import writer


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

