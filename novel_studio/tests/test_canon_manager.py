from novel_app.nodes.canon_manager import canon_commit


def test_canon_commit_merges_character_state_and_dedupes_world_facts() -> None:
    state = {
        "current_card": {"chapter_no": 2},
        "current_draft": {
            "summary_100w": "主角确认执事反应异常，并拿到新的线索。",
            "canon_delta_candidate": {
                "character_updates": [
                    {
                        "character_id": "mc",
                        "known_facts_add": ["执事听到旧案后停顿", "执事听到旧案后停顿"],
                        "active_goals_add": ["确认执事是否涉案"],
                        "location": "禁地外围",
                    }
                ],
                "world_updates": [
                    {"type": "hint", "value": "禁地炉火与旧案有关"},
                    {"type": "hint", "value": "禁地炉火与旧案有关"},
                ],
                "loop_updates": [
                    {"id": "hook_1", "status": "resolved"},
                    {"id": "hook_2", "status": "active", "question": "旧案核心证据在哪"},
                ],
            },
        },
        "canon_state": {
            "story_clock": {"current_arc": 1, "current_chapter": 1, "in_story_time": "day_1"},
            "character_states": {
                "mc": {
                    "character_id": "mc",
                    "known_facts": ["受罚另有原因"],
                    "active_goals": ["活下去"],
                    "location": "惩戒场",
                }
            },
            "world_facts": ["hint:禁地炉火与旧案有关"],
            "open_loops": [
                {"id": "hook_1", "status": "active", "question": "谁在推动旧案掩盖"},
                {"id": "hook_old", "status": "active", "question": "导师为何缺席"},
            ],
        },
    }

    result = canon_commit(state)
    canon = result["canon_state"]

    assert canon["story_clock"]["current_chapter"] == 2
    assert canon["character_states"]["mc"]["location"] == "禁地外围"
    assert canon["character_states"]["mc"]["known_facts"] == ["受罚另有原因", "执事听到旧案后停顿"]
    assert canon["character_states"]["mc"]["active_goals"] == ["活下去", "确认执事是否涉案"]
    assert canon["world_facts"] == ["hint:禁地炉火与旧案有关"]
    assert canon["open_loops"] == [
        {"id": "hook_old", "status": "active", "question": "导师为何缺席"},
        {"id": "hook_2", "status": "active", "question": "旧案核心证据在哪"},
    ]
    assert "canon_committed:2" in result["event_log"]


def test_canon_commit_creates_defaults_when_missing() -> None:
    result = canon_commit(
        {
            "current_card": {"chapter_no": 1},
            "current_draft": {"summary_100w": "测试", "canon_delta_candidate": {}},
        }
    )

    canon = result["canon_state"]
    assert canon["story_clock"]["current_arc"] == 1
    assert canon["story_clock"]["current_chapter"] == 1
    assert canon["world_facts"] == []
    assert canon["open_loops"] == []
