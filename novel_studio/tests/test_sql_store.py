from pathlib import Path

from novel_app.services.sql_store import SqlAlchemyStore


def test_sql_store_persists_project_and_run(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'novel_studio.db'}"
    store = SqlAlchemyStore(database_url)
    store.create_tables()

    project = store.create_project(
        name="测试项目",
        description=None,
        default_user_brief={"title": "长夜炉火"},
        default_target_chapters=2,
    )
    run = store.save_run(
        project_id=project.project_id,
        status="completed",
        request={"target_chapters": 2, "operator_id": "tester", "user_brief": {"title": "长夜炉火"}},
        result={"phase_decision": {"final_decision": "pass"}},
        error=None,
    )
    store.save_run_outputs(
        run=run,
        result={
            "current_card": {"chapter_no": 2},
            "current_draft": {"title": "第2章 测试"},
            "publish_package": {"chapter_no": 2, "title": "第2章 测试"},
            "phase_decision": {"final_decision": "pass"},
            "feedback_summary": {"chapter_no": 2},
            "canon_state": {"story_clock": {"current_chapter": 2}},
            "latest_review_reports": [{"reviewer": "style"}],
            "event_log": ["done"],
        },
    )
    approval = store.create_approval_request(
        project_id=project.project_id,
        run_id=run.run_id,
        chapter_no=2,
        requested_action="continue",
        reason="需要人工确认",
        payload={"source": "test"},
    )
    resolved = store.resolve_approval_request(
        approval_id=approval.approval_id,
        decision="approved",
        operator_id="editor-1",
        comment="通过",
    )

    assert store.get_project(project.project_id) is not None
    assert store.get_run(run.run_id) is not None
    assert len(store.list_projects()) == 1
    assert len(store.list_chapters(project.project_id)) == 1
    assert len(store.list_artifacts(run.run_id)) >= 1
    assert store.get_approval_request(approval.approval_id) is not None
    assert resolved is not None
    assert resolved.status == "approved"


def test_sql_store_running_run_has_no_finished_at_until_terminal_state(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'novel_studio.db'}"
    store = SqlAlchemyStore(database_url)
    store.create_tables()

    project = store.create_project(
        name="测试项目",
        description=None,
        default_user_brief={"title": "长夜炉火"},
        default_target_chapters=1,
    )
    run = store.save_run(
        project_id=project.project_id,
        status="running",
        request={"target_chapters": 1, "operator_id": "tester", "user_brief": {"title": "长夜炉火"}},
        result={"progress": {"latest_event": "run_started"}},
        error=None,
    )

    assert run.finished_at is None

    completed = store.update_run(
        run_id=run.run_id,
        status="completed",
        result={"phase_decision": {"final_decision": "pass"}},
        error=None,
    )

    assert completed is not None
    assert completed.finished_at is not None
