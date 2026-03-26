from novel_app.config import AppConfig
from novel_app.graph_main import graph


def test_graph_runs_multi_chapter_stub_flow(monkeypatch) -> None:
    monkeypatch.setenv("NOVEL_STUDIO_STUB_MODE", "true")

    result = graph.invoke(
        {
            "user_brief": {
                "title": "长夜炉火",
                "genre": "东方玄幻",
                "platform": "起点中文网",
                "hook": "一个被逐出山门的外门弟子，靠偷听禁地炉火中的古老对话逆天改命。",
                "must_have": ["稳步升级", "师门阴谋", "章末钩子强"],
                "must_not_have": ["后宫泛滥", "无代价外挂"],
            },
            "target_chapters": 2,
        },
        context=AppConfig(
            stub_mode=True,
            openai_api_key=None,
            admin_token=None,
            database_url="sqlite:///./test.db",
            model_name="gpt-5-nano",
            project_id="demo-book",
            operator_id="test-suite",
        ).to_runtime_context(),
    )

    assert result["phase_decision"]["final_decision"] == "pass"
    assert result["publish_package"]["chapter_no"] == 2
    assert result["canon_state"]["story_clock"]["current_chapter"] == 2
    assert "phase_decision:rewrite" in result["event_log"]
    assert "phase_decision:pass" in result["event_log"]
