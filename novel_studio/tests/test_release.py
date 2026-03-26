from novel_app.nodes.release import release_prepare


def test_release_prepare_builds_richer_publish_package() -> None:
    result = release_prepare(
        {
            "current_card": {
                "chapter_no": 2,
                "hook": {"chapter_end_question": "主角是否会冒险进入禁地？"},
            },
            "current_draft": {
                "title": "第2章 火光后的停顿",
                "summary_100w": "主角确认执事异样，并决定继续试探。",
                "content": "第一段。\n第二段。",
            },
            "phase_decision": {"final_decision": "pass"},
            "review_reports": [
                {"reviewer": "continuity", "decision": "pass", "issues": []},
                {"reviewer": "style", "decision": "pass", "issues": [{"severity": "minor"}]},
            ],
            "canon_state": {
                "story_clock": {"current_arc": 1, "current_chapter": 2},
                "open_loops": [{"id": "hook_2", "status": "active"}],
                "last_chapter_summary": "上一章摘要",
            },
            "human_instruction": {"comment": "保留疑点，不要过早揭底"},
        }
    )

    package = result["publish_package"]

    assert package["chapter_no"] == 2
    assert package["title"] == "第2章 火光后的停顿"
    assert package["full_text"] == "第一段。\n第二段。"
    assert package["word_count"] == 8
    assert package["chapter_end_question"] == "主角是否会冒险进入禁地？"
    assert package["reviewer_summary"]["final_decision"] == "pass"
    assert package["reviewer_summary"]["minor_issue_count"] == 1
    assert package["canon_snapshot"]["open_loop_ids"] == ["hook_2"]
    assert package["operator_notes"] == "保留疑点，不要过早揭底"
