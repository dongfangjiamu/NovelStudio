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
            "planning_context": {"chapter_no": 2, "applied_guardrails": ["主角主动性前置"]},
            "current_card": {"chapter_no": 2},
            "drafting_context": {"chapter_no": 2, "applied_guardrails": ["章末必须升级风险"]},
            "current_draft": {"title": "第2章 测试"},
            "publish_package": {"chapter_no": 2, "title": "第2章 测试"},
            "phase_decision": {"final_decision": "pass"},
            "feedback_summary": {"chapter_no": 2},
            "chapter_lesson": {"chapter_no": 2, "pass_reasons": ["通过"]},
            "writer_playbook": {"version": 1, "always_apply": ["保持章节目的明确"]},
            "issue_ledger": {"chapter_no": 2, "status": "cleared", "open_count": 0, "issues": []},
            "review_resolution_trace": {"chapter_no": 2, "resolved_count": 1, "items": [{"issue_id": "iss_1"}]},
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
    artifact_types = {item.artifact_type for item in store.list_artifacts(run.run_id)}
    assert "planning_context" in artifact_types
    assert "drafting_context" in artifact_types
    assert "chapter_lesson" in artifact_types
    assert "writer_playbook" in artifact_types
    assert "issue_ledger" in artifact_types
    assert "review_resolution_trace" in artifact_types
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


def test_sql_store_persists_conversation_threads_and_messages(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'novel_studio.db'}"
    store = SqlAlchemyStore(database_url)
    store.create_tables()

    project = store.create_project(
        name="对话项目",
        description=None,
        default_user_brief={"title": "长夜炉火"},
        default_target_chapters=1,
    )
    thread = store.create_conversation_thread(
        project_id=project.project_id,
        scope="project_bootstrap",
        title="项目共创对话",
        linked_run_id=None,
        linked_chapter_no=None,
    )
    opening = store.add_conversation_message(
        thread_id=thread.thread_id,
        role="assistant",
        message_type="assistant_question",
        content="我们先把这本书的创作方向问清楚。",
        structured_payload={"suggested_topics": ["核心爽点"]},
    )
    user = store.add_conversation_message(
        thread_id=thread.thread_id,
        role="user",
        message_type="user_message",
        content="主角要克制，但行动要果断。",
        structured_payload={"operator_id": "tester"},
    )

    assert opening is not None
    assert user is not None
    threads = store.list_conversation_threads(project.project_id)
    messages = store.list_conversation_messages(thread.thread_id)
    assert len(threads) == 1
    assert threads[0].updated_at == user.created_at
    assert len(messages) == 2
    assert messages[0].role == "assistant"
    assert messages[1].role == "user"


def test_sql_store_persists_conversation_decisions(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'novel_studio.db'}"
    store = SqlAlchemyStore(database_url)
    store.create_tables()

    project = store.create_project(
        name="对话项目",
        description=None,
        default_user_brief={"title": "长夜炉火"},
        default_target_chapters=1,
    )
    thread = store.create_conversation_thread(
        project_id=project.project_id,
        scope="rewrite_intervention",
        title="第1章修稿协作",
        linked_run_id="run_demo",
        linked_chapter_no=1,
    )
    message = store.add_conversation_message(
        thread_id=thread.thread_id,
        role="user",
        message_type="user_message",
        content="保留主角克制感，但把冲突前置。",
        structured_payload={"operator_id": "tester"},
    )

    assert message is not None
    decision = store.create_conversation_decision(
        project_id=project.project_id,
        thread_id=thread.thread_id,
        message_id=message.message_id,
        decision_type="human_instruction",
        payload={"comment": "保留主角克制感，但把冲突前置。"},
        applied_to_run_id=thread.linked_run_id,
        applied_to_chapter_no=thread.linked_chapter_no,
    )

    decisions = store.list_conversation_decisions(project_id=project.project_id)
    assert decision.decision_id == decisions[0].decision_id
    assert decisions[0].decision_type == "human_instruction"
