from types import SimpleNamespace

from novel_app.services.store import ProjectRecord
from novel_app.services.workflow import WorkflowService


def test_run_graph_reports_current_node(monkeypatch) -> None:
    observed: list[tuple[str | None, list[str]]] = []

    def fake_stream(input_state, *, context, stream_mode):
        assert stream_mode == ["updates", "values"]
        yield ("values", {"event_log": []})
        yield ("updates", {"interviewer_contract": {"event_log": ["creative_contract_ready"]}})
        yield ("values", {"event_log": ["creative_contract_ready"]})
        yield ("updates", {"lore_builder": {"event_log": ["story_bible_ready"]}})
        yield ("values", {"event_log": ["creative_contract_ready", "story_bible_ready"]})

    monkeypatch.setattr("novel_app.services.workflow.graph.stream", fake_stream)

    result = WorkflowService._run_graph(
        input_state={"user_brief": {"title": "x"}, "target_chapters": 1},
        context=SimpleNamespace(),
        on_update=lambda current_node, state: observed.append((current_node, list(state.get("event_log", [])))),
    )

    assert result["event_log"] == ["creative_contract_ready", "story_bible_ready"]
    assert observed == [
        (None, []),
        ("interviewer_contract", ["creative_contract_ready"]),
        ("lore_builder", ["creative_contract_ready", "story_bible_ready"]),
    ]


def test_prepare_project_request_uses_defaults() -> None:
    service = WorkflowService(
        SimpleNamespace(
            operator_id="system",
            model_name="gpt-5.4",
            openai_base_url="https://relay.example.com/openai",
        )
    )
    project = ProjectRecord(
        project_id="proj_1",
        name="demo",
        description=None,
        default_user_brief={"title": "默认标题"},
        default_target_chapters=2,
        created_at="2026-03-26T00:00:00+00:00",
    )

    request_payload = service.prepare_project_request(
        project=project,
        user_brief=None,
        target_chapters=None,
        operator_id=None,
    )

    assert request_payload == {
        "user_brief": {"title": "默认标题"},
        "target_chapters": 2,
        "operator_id": "system",
    }
