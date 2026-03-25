from novel_app.schemas import ChapterCard, CreativeContract


def test_creative_contract_validation() -> None:
    contract = CreativeContract(
        project={
            "working_title": "测试书",
            "platform": "起点中文网",
            "genre": "东方玄幻",
            "chapter_words_target": 3000,
            "total_words_target": 1000000,
            "update_cadence": "daily",
        },
        reader_promise={
            "one_sentence_hook": "一个被逐出师门的弟子，靠禁地里的秘密翻盘。",
            "primary_selling_points": ["强钩子"],
        },
        control_panel={
            "pacing": 4,
            "payoff_density": 4,
            "romance_weight": 2,
            "prose_flourish": 2,
        },
        non_negotiables={
            "must_have": ["升级"],
            "must_not_have": ["设定破例"],
        },
    )
    assert contract.project.genre == "东方玄幻"


def test_chapter_card_requires_two_scene_beats() -> None:
    card = ChapterCard(
        chapter_no=1,
        purpose="建立主角困境",
        pov="third_limited_mc",
        entry_state={
            "required_context": [],
            "emotional_state": "压抑",
            "unresolved_threads": [],
        },
        scene_beats=[
            {"goal": "撑过去", "conflict": "受罚", "turn": "听见异常"},
            {"goal": "掩饰自己", "conflict": "执事盯上他", "turn": "确认旧案线索"},
        ],
        must_include=[],
        must_not_change=[],
        hook={
            "chapter_end_question": "第二道声音是谁？",
            "target_reader_impulse": "must_click_next",
        },
        word_count_target=2800,
    )
    assert len(card.scene_beats) == 2
