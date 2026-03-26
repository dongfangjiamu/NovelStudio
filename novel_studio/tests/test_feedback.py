from novel_app.nodes.feedback import feedback_ingest


def test_feedback_ingest_generates_chapter_lesson_and_writer_playbook() -> None:
    result = feedback_ingest(
        {
            "current_card": {
                "chapter_no": 1,
                "purpose": "让主角第一次主动试探执事反应",
            },
            "publish_package": {
                "title": "第1章 炉火异响",
                "chapter_end_question": "主角要不要冒险靠近禁地炉火？",
            },
            "review_reports": [
                {
                    "reviewer": "pacing",
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
                    "reviewer": "reader_sim",
                    "issues": [
                        {
                            "severity": "major",
                            "type": "hook",
                            "evidence": "章末风险升级还可以更明确。",
                            "fix_instruction": "把章末问句落到更危险的选择上。",
                        }
                    ],
                },
            ],
            "rewrite_count": 1,
            "human_instruction": {
                "comment": "保留主角主动性，把试探前置。",
                "reason": "先把主角能动性立住",
            },
            "issue_ledger": {
                "chapter_no": 1,
                "status": "needs_revision",
                "open_count": 2,
                "new_count": 1,
                "recurring_count": 1,
                "resolved_count": 0,
                "progress_summary": "已解决 0 项，复发 1 项，新增 1 项。",
                "issues": [
                    {
                        "issue_id": "iss_1",
                        "category": "pacing",
                        "evidence": "主角主动试探来得偏晚。",
                        "fix_instruction": "让主角更早做出一次带风险的小试探。",
                        "status": "open",
                    },
                    {
                        "issue_id": "iss_2",
                        "category": "hook",
                        "evidence": "章末风险升级还可以更明确。",
                        "fix_instruction": "把章末问句落到更危险的选择上。",
                        "status": "open",
                    },
                ],
            },
            "chapters_completed": 0,
        }
    )

    lesson = result["chapter_lesson"]
    playbook = result["writer_playbook"]

    assert lesson["chapter_no"] == 1
    assert lesson["rewrite_count"] == 1
    assert lesson["issue_ledger_status"] == "needs_revision"
    assert lesson["open_issue_count"] == 2
    assert lesson["new_issue_count"] == 1
    assert lesson["recurring_issue_count"] == 1
    assert lesson["issue_progress_summary"] == "已解决 0 项，复发 1 项，新增 1 项。"
    assert any("带风险的小试探" in item for item in lesson["carry_forward_rules"])
    assert any("升级风险" in item for item in lesson["discarded_patterns"])

    assert playbook["version"] == 1
    assert playbook["last_chapter_no"] == 1
    assert any("继续保证章末存在明确的下一章驱动力。" == item for item in playbook["always_apply"])
    assert any("经过 1 轮修订后" in item for item in playbook["validated_patterns"])
    assert result["feedback_summary"]["playbook_version"] == 1
