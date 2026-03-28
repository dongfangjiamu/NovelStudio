import time
from datetime import datetime, timedelta, timezone
from threading import Event

from fastapi.testclient import TestClient

from novel_app.api.app import create_app
from novel_app.config import AppConfig
from novel_app.services.store import InMemoryStore
from novel_app.services.workflow import WorkflowService


def make_client() -> TestClient:
    app = create_app(
        config=AppConfig(
            stub_mode=True,
            openai_api_key=None,
            admin_token=None,
            database_url="sqlite:///:memory:",
            model_name="gpt-5-nano",
            project_id="api-test",
            operator_id="tester",
        ),
        store=InMemoryStore(),
    )
    return TestClient(app)


def wait_for_run(client: TestClient, run_id: str, *, timeout: float = 2.0) -> dict:
    deadline = time.time() + timeout
    last_payload = None
    while time.time() < deadline:
        response = client.get(f"/api/runs/{run_id}")
        assert response.status_code == 200
        last_payload = response.json()
        if last_payload["status"] != "running":
            return last_payload
        time.sleep(0.02)
    raise AssertionError(f"run did not finish in time: {run_id} last={last_payload}")


def test_healthz() -> None:
    client = make_client()

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["stub_mode"] is True
    assert response.json()["auth_mode"] == "open"
    assert response.json()["database"]["status"] == "ready"
    assert response.json()["database"]["backend"] == "inmemory"


def test_business_metrics_exposes_system_and_project_views() -> None:
    client = make_client()

    project = client.post(
        "/api/projects",
        json={
            "name": "指标项目",
            "default_user_brief": {"title": "长夜炉火", "genre": "东方玄幻"},
            "default_target_chapters": 1,
        },
    ).json()

    run = client.post(
        f"/api/projects/{project['project_id']}/runs",
        json={"operator_id": "tester"},
    ).json()
    wait_for_run(client, run["run_id"])

    client.post(
        f"/api/runs/{run['run_id']}/approval-requests",
        json={"requested_action": "continue", "reason": "需要人工确认"},
    )

    system_metrics = client.get("/api/business-metrics")
    project_metrics = client.get(f"/api/business-metrics?project_id={project['project_id']}")

    assert system_metrics.status_code == 200
    assert project_metrics.status_code == 200
    assert system_metrics.json()["scope"] == "system"
    assert project_metrics.json()["scope"] == "project"
    assert project_metrics.json()["project_id"] == project["project_id"]
    assert len(system_metrics.json()["cards"]) == 4
    assert len(project_metrics.json()["cards"]) == 4
    assert len(system_metrics.json()["sections"]) == 3
    assert len(project_metrics.json()["sections"]) == 3
    assert any(card["label"] == "开书状态" for card in project_metrics.json()["cards"])
    assert system_metrics.json()["sections"][0]["title"] == "常见卡点"
    assert project_metrics.json()["sections"][1]["title"] == "恢复路径结果"


def test_strategy_suggestions_expose_system_and_project_recommendations() -> None:
    client = make_client()

    project = client.post(
        "/api/projects",
        json={
            "name": "建议项目",
            "default_user_brief": {"title": "长夜炉火", "genre": "东方玄幻"},
            "default_target_chapters": 1,
        },
    ).json()

    run = client.post(
        f"/api/projects/{project['project_id']}/runs",
        json={"operator_id": "tester"},
    ).json()
    completed = wait_for_run(client, run["run_id"])
    assert completed["status"] in {"completed", "awaiting_approval"}

    approval = client.post(
        f"/api/runs/{run['run_id']}/approval-requests",
        json={"requested_action": "rewrite", "reason": "正文表达还不稳"},
    ).json()
    client.post(
        f"/api/approval-requests/{approval['approval_id']}/resolve",
        json={"decision": "approved", "operator_id": "tester", "comment": "先按建议恢复"},
    )

    system_suggestions = client.get("/api/strategy-suggestions")
    project_suggestions = client.get(f"/api/strategy-suggestions?project_id={project['project_id']}")

    assert system_suggestions.status_code == 200
    assert project_suggestions.status_code == 200
    assert system_suggestions.json()["scope"] == "system"
    assert project_suggestions.json()["scope"] == "project"
    assert project_suggestions.json()["project_id"] == project["project_id"]
    assert len(system_suggestions.json()["items"]) >= 1
    assert len(project_suggestions.json()["items"]) >= 1
    assert "当前进化建议" in system_suggestions.json()["headline"]
    assert "当前进化建议" in project_suggestions.json()["headline"]


def test_strategy_suggestion_can_be_adopted_into_project_rules() -> None:
    client = make_client()

    project = client.post(
        "/api/projects",
        json={
            "name": "策略采纳项目",
            "default_user_brief": {"title": "长夜炉火", "genre": "东方玄幻"},
            "default_target_chapters": 1,
        },
    ).json()

    app = client.app
    run = app.state.store.save_run(
        project_id=project["project_id"],
        status="completed",
        request={"user_brief": project["default_user_brief"], "target_chapters": 1, "operator_id": "tester"},
        result={
            "issue_ledger": {
                "chapter_no": 1,
                "status": "needs_revision",
                "open_count": 2,
                "issues": [
                    {"issue_id": "iss_1", "category": "pacing", "status": "open"},
                    {"issue_id": "iss_2", "category": "hook", "status": "recurring"},
                ],
            }
        },
        error=None,
    )
    app.state.store.save_run_outputs(run=run, result=run.result or {})

    suggestions = client.get(f"/api/strategy-suggestions?project_id={project['project_id']}")
    assert suggestions.status_code == 200
    item = next((entry for entry in suggestions.json()["items"] if entry["suggestion_key"] == "codify_pacing_and_hook_rules"), None)
    assert item is not None
    assert item["can_adopt"] is True

    adopt = client.post(
        f"/api/projects/{project['project_id']}/strategy-suggestions/codify_pacing_and_hook_rules/actions",
        json={"action": "adopt"},
    )
    assert adopt.status_code == 200
    assert adopt.json()["status"] == "adopted"
    assert adopt.json()["adopted_decision_id"]

    decisions = client.get(f"/api/projects/{project['project_id']}/conversation-decisions")
    assert decisions.status_code == 200
    assert any(item["decision_type"] == "writer_playbook_rule" for item in decisions.json())

    suggestions_after = client.get(f"/api/strategy-suggestions?project_id={project['project_id']}")
    assert suggestions_after.status_code == 200
    assert all(item["suggestion_key"] != "codify_pacing_and_hook_rules" for item in suggestions_after.json()["items"])


def test_project_create_and_list() -> None:
    client = make_client()

    create_response = client.post(
        "/api/projects",
        json={
            "name": "测试项目",
            "description": "alpha",
            "default_user_brief": {"title": "长夜炉火", "genre": "东方玄幻"},
            "default_target_chapters": 2,
        },
    )
    list_response = client.get("/api/projects")

    assert create_response.status_code == 201
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["name"] == "测试项目"


def test_conversation_thread_flow() -> None:
    client = make_client()
    project = client.post(
        "/api/projects",
        json={
            "name": "对话项目",
            "default_user_brief": {"title": "长夜炉火", "genre": "东方玄幻"},
            "default_target_chapters": 1,
        },
    ).json()

    create_thread = client.post(
        f"/api/projects/{project['project_id']}/conversation-threads",
        json={"scope": "project_bootstrap"},
    )

    assert create_thread.status_code == 201
    thread = create_thread.json()
    assert thread["scope"] == "project_bootstrap"
    assert thread["message_count"] == 1
    assert "立项共创" in thread["title"]
    assert thread["interview_state"]["completion_label"] == "0/4"
    assert thread["interview_state"]["unresolved_topics"][0] == "最想保住的吸引力"
    assert thread["interview_state"]["next_options"][0] == "爽感往上冲"

    list_threads = client.get(f"/api/projects/{project['project_id']}/conversation-threads")
    assert list_threads.status_code == 200
    assert list_threads.json()[0]["thread_id"] == thread["thread_id"]

    initial_messages = client.get(f"/api/conversation-threads/{thread['thread_id']}/messages")
    assert initial_messages.status_code == 200
    assert initial_messages.json()[0]["role"] == "assistant"
    assert "先别急着定义卖点" in initial_messages.json()[0]["content"]

    reply = client.post(
        f"/api/conversation-threads/{thread['thread_id']}/messages",
        json={"content": "我想把主角写成克制型，但前期行动要更果断。"},
    )
    assert reply.status_code == 201
    created_messages = reply.json()
    assert len(created_messages) == 2
    assert created_messages[0]["role"] == "user"
    assert created_messages[1]["role"] == "assistant"

    refreshed_thread = client.get(f"/api/conversation-threads/{thread['thread_id']}")
    assert refreshed_thread.status_code == 200
    assert refreshed_thread.json()["message_count"] == 3
    assert refreshed_thread.json()["interview_state"]["completion_label"] == "1/4"
    assert refreshed_thread.json()["interview_state"]["confirmed_topics"] == ["最想保住的吸引力"]
    assert refreshed_thread.json()["interview_state"]["unresolved_topics"][0] == "主角行动方式"

    adopted = client.post(
        f"/api/conversation-messages/{created_messages[0]['message_id']}/adopt",
        json={"decision_type": "writer_playbook_rule"},
    )
    assert adopted.status_code == 201
    assert "克制型" in adopted.json()["summary"]
    assert "克制型" in adopted.json()["content"]

    thread_after_adopt = client.get(f"/api/conversation-threads/{thread['thread_id']}")
    assert thread_after_adopt.status_code == 200
    assert "克制型" in thread_after_adopt.json()["interview_state"]["adopted_highlights"][0]


def test_project_bootstrap_opening_uses_idea_seed() -> None:
    client = make_client()
    project = client.post(
        "/api/projects",
        json={
            "name": "灵感立项项目",
            "default_user_brief": {
                "title": "炉火残卷",
                "idea_seed": "我先只抓住一个感觉：一个被逐出山门的人，在禁地炉火前偷听到不该听见的古老声音。",
                "idea_seed_type": "scene",
                "capture_stage": "seed",
            },
            "default_target_chapters": 1,
        },
    ).json()

    thread = client.post(
        f"/api/projects/{project['project_id']}/conversation-threads",
        json={"scope": "project_bootstrap"},
    ).json()
    messages = client.get(f"/api/conversation-threads/{thread['thread_id']}/messages")

    assert messages.status_code == 200
    assert "我先接住你现在手里这点材料" in messages.json()[0]["content"]
    assert "被逐出山门的人" in messages.json()[0]["content"]
    assert thread["interview_state"]["basis"][1].startswith("灵感类型：scene")


def test_conversation_scene_scopes_seed_targeted_opening_messages() -> None:
    client = make_client()
    project = client.post(
        "/api/projects",
        json={
            "name": "场景对话项目",
            "default_user_brief": {"title": "长夜炉火", "genre": "东方玄幻"},
            "default_target_chapters": 1,
        },
    ).json()

    character_thread = client.post(
        f"/api/projects/{project['project_id']}/conversation-threads",
        json={"scope": "character_room"},
    )
    outline_thread = client.post(
        f"/api/projects/{project['project_id']}/conversation-threads",
        json={"scope": "outline_room"},
    )

    assert character_thread.status_code == 201
    assert outline_thread.status_code == 201
    assert character_thread.json()["title"] == "人物讨论"
    assert outline_thread.json()["title"] == "大纲讨论"
    assert character_thread.json()["interview_state"]["goal"].startswith("把人物感觉逐步收紧")
    assert outline_thread.json()["interview_state"]["goal"].startswith("把第一卷怎么往前推逐步聊清楚")

    character_messages = client.get(f"/api/conversation-threads/{character_thread.json()['thread_id']}/messages")
    outline_messages = client.get(f"/api/conversation-threads/{outline_thread.json()['thread_id']}/messages")

    assert "人物讨论线程" in character_messages.json()[0]["content"]
    assert "先回答第 1 问" in character_messages.json()[0]["content"]
    assert "如果只用一个感觉描述主角" in character_messages.json()[0]["content"]
    assert "大纲讨论线程" in outline_messages.json()[0]["content"]
    assert "第一卷最主要靠什么把读者往下带" in outline_messages.json()[0]["content"]


def test_interview_helpers_can_rephrase_expand_and_skip_without_wrong_progress() -> None:
    client = make_client()
    project = client.post(
        "/api/projects",
        json={
            "name": "采访辅助项目",
            "default_user_brief": {"title": "长夜炉火", "idea_seed": "一个被流放的人，靠炉火秘密翻身。"},
            "default_target_chapters": 1,
        },
    ).json()

    thread = client.post(
        f"/api/projects/{project['project_id']}/conversation-threads",
        json={"scope": "project_bootstrap"},
    ).json()

    more_options = client.post(
        f"/api/conversation-threads/{thread['thread_id']}/messages",
        json={"content": "给我更多选项。"},
    )
    assert more_options.status_code == 201
    thread_after_options = client.get(f"/api/conversation-threads/{thread['thread_id']}").json()
    assert thread_after_options["interview_state"]["completion_label"] == "0/4"
    assert "压迫中翻盘" in thread_after_options["interview_state"]["next_options"]

    rephrase = client.post(
        f"/api/conversation-threads/{thread['thread_id']}/messages",
        json={"content": "换个问法。"},
    )
    assert rephrase.status_code == 201
    thread_after_rephrase = client.get(f"/api/conversation-threads/{thread['thread_id']}").json()
    assert thread_after_rephrase["interview_state"]["completion_label"] == "0/4"
    assert "只保住一种读者体验" in thread_after_rephrase["interview_state"]["next_prompt"]

    skip = client.post(
        f"/api/conversation-threads/{thread['thread_id']}/messages",
        json={"content": "先跳过这个问题，继续问下一个。"},
    )
    assert skip.status_code == 201
    thread_after_skip = client.get(f"/api/conversation-threads/{thread['thread_id']}").json()
    assert thread_after_skip["interview_state"]["completion_label"] == "1/4"
    assert thread_after_skip["interview_state"]["skipped_topics"] == ["最想保住的吸引力"]
    assert thread_after_skip["interview_state"]["unresolved_topics"][0] == "主角行动方式"


def test_off_topic_interview_answer_does_not_silently_advance_stage() -> None:
    client = make_client()
    project = client.post(
        "/api/projects",
        json={
            "name": "采访纠偏项目",
            "default_user_brief": {"title": "长夜炉火", "idea_seed": "一个被逐出山门的人，靠炉火秘密翻身。"},
            "default_target_chapters": 1,
        },
    ).json()

    thread = client.post(
        f"/api/projects/{project['project_id']}/conversation-threads",
        json={"scope": "character_room"},
    ).json()

    first_answer = client.post(
        f"/api/conversation-threads/{thread['thread_id']}/messages",
        json={"content": "他表面克制，内里一直压着不甘和报复心。"},
    )
    assert first_answer.status_code == 201

    off_topic = client.post(
        f"/api/conversation-threads/{thread['thread_id']}/messages",
        json={"content": "我希望他不是莽，而是越到绝境越冷静。"},
    )
    assert off_topic.status_code == 201
    assert "先不急着算作已确认结论" in off_topic.json()[1]["content"]

    refreshed = client.get(f"/api/conversation-threads/{thread['thread_id']}")
    assert refreshed.status_code == 200
    assert refreshed.json()["interview_state"]["completion_label"] == "1/4"
    assert refreshed.json()["interview_state"]["next_topic_title"] == "主角真正想摆脱什么"
    assert refreshed.json()["interview_state"]["last_helper_action"] == "clarify"


def test_interview_state_builds_current_draft_after_two_answers() -> None:
    client = make_client()
    project = client.post(
        "/api/projects",
        json={
            "name": "采访草案项目",
            "default_user_brief": {"title": "长夜炉火", "idea_seed": "一个被逐出山门的人，靠炉火中的古老声音翻盘。"},
            "default_target_chapters": 1,
        },
    ).json()

    thread = client.post(
        f"/api/projects/{project['project_id']}/conversation-threads",
        json={"scope": "project_bootstrap"},
    ).json()

    client.post(
        f"/api/conversation-threads/{thread['thread_id']}/messages",
        json={"content": "我最想保住的是压迫中翻盘和悬念感。"},
    )
    client.post(
        f"/api/conversation-threads/{thread['thread_id']}/messages",
        json={"content": "主角要是那种克制但危险的人，平时忍着，关键时刻会立刻动手。"},
    )

    refreshed = client.get(f"/api/conversation-threads/{thread['thread_id']}").json()
    draft = refreshed["interview_state"]["current_draft"]
    stage = refreshed["interview_state"]["stage_confirmation"]

    assert draft["title"] == "当前理解草案"
    assert len(draft["sections"]) == 2
    assert draft["sections"][0]["label"] == "最想保住的吸引力"
    assert draft["sections"][1]["label"] == "主角行动方式"
    assert "《长夜炉火》" in draft["lead"]
    assert stage["confirmed_items"][0]["label"] == "最想保住的吸引力"
    assert stage["provisional_items"][1]["label"] == "主角行动方式"
    assert stage["open_questions"][0] == "故事推进方式"
    assert stage["next_steps"][0]["scope"] == "character_room"
    assert stage["next_steps"][1]["scope"] == "outline_room"
    assert stage["project_summary"]["title"] == "第一版项目设定摘要"
    assert stage["decision_split_preview"]["counts"]["character_note"] == 1
    assert stage["decision_split_preview"]["counts"]["writer_playbook_rule"] == 1
    assert stage["action_recommendation"]["mode"] == "continue_clarifying"
    assert stage["action_recommendation"]["focus_topic"] == "故事推进方式"


def test_draft_confirm_helper_does_not_advance_progress() -> None:
    client = make_client()
    project = client.post(
        "/api/projects",
        json={
            "name": "草案确认项目",
            "default_user_brief": {"title": "长夜炉火", "idea_seed": "一个被逐出山门的人，靠炉火中的古老声音翻盘。"},
            "default_target_chapters": 1,
        },
    ).json()

    thread = client.post(
        f"/api/projects/{project['project_id']}/conversation-threads",
        json={"scope": "project_bootstrap"},
    ).json()
    client.post(
        f"/api/conversation-threads/{thread['thread_id']}/messages",
        json={"content": "我最想保住的是压迫中翻盘和悬念感。"},
    )
    client.post(
        f"/api/conversation-threads/{thread['thread_id']}/messages",
        json={"content": "主角要是那种克制但危险的人，平时忍着，关键时刻会立刻动手。"},
    )
    confirm = client.post(
        f"/api/conversation-threads/{thread['thread_id']}/messages",
        json={"content": "这版理解基本对，请继续细化。"},
    )

    assert confirm.status_code == 201
    refreshed = client.get(f"/api/conversation-threads/{thread['thread_id']}").json()
    assert refreshed["interview_state"]["completion_label"] == "2/4"
    assert refreshed["interview_state"]["last_helper_action"] == "draft_confirm"


def test_project_bootstrap_summary_can_be_applied_to_project_brief() -> None:
    client = make_client()
    project = client.post(
        "/api/projects",
        json={
            "name": "阶段摘要项目",
            "default_user_brief": {"title": "长夜炉火", "idea_seed": "一个被逐出山门的人，靠炉火中的古老声音翻盘。"},
            "default_target_chapters": 1,
        },
    ).json()

    thread = client.post(
        f"/api/projects/{project['project_id']}/conversation-threads",
        json={"scope": "project_bootstrap"},
    ).json()
    client.post(
        f"/api/conversation-threads/{thread['thread_id']}/messages",
        json={"content": "我最想保住的是压迫中翻盘和悬念感。"},
    )
    client.post(
        f"/api/conversation-threads/{thread['thread_id']}/messages",
        json={"content": "主角要是那种克制但危险的人，平时忍着，关键时刻会立刻动手。"},
    )

    applied = client.post(f"/api/conversation-threads/{thread['thread_id']}/apply-project-summary")

    assert applied.status_code == 200
    brief = applied.json()["default_user_brief"]
    assert brief["capture_stage"] == "clarified"
    assert brief["project_summary"]["title"] == "第一版项目设定摘要"
    assert brief["project_summary"]["source_thread_id"] == thread["thread_id"]
    assert brief["intent_profile"]["reader_pull"] == "我最想保住的是压迫中翻盘和悬念感。"
    assert brief["intent_profile"]["protagonist_mode"] == "主角要是那种克制但危险的人，平时忍着，关键时刻会立刻动手。"

    refreshed_thread = client.get(f"/api/conversation-threads/{thread['thread_id']}")
    messages = client.get(f"/api/conversation-threads/{thread['thread_id']}/messages").json()
    assert refreshed_thread.status_code == 200
    assert any("已把这版阶段确认摘要写回项目设定" in item["content"] for item in messages)


def test_project_bootstrap_stage_summary_can_split_into_decisions() -> None:
    client = make_client()
    project = client.post(
        "/api/projects",
        json={
            "name": "阶段拆分项目",
            "default_user_brief": {"title": "长夜炉火", "idea_seed": "一个被逐出山门的人，靠炉火中的古老声音翻盘。"},
            "default_target_chapters": 1,
        },
    ).json()

    thread = client.post(
        f"/api/projects/{project['project_id']}/conversation-threads",
        json={"scope": "project_bootstrap"},
    ).json()
    client.post(
        f"/api/conversation-threads/{thread['thread_id']}/messages",
        json={"content": "我最想保住的是压迫中翻盘和悬念感。"},
    )
    client.post(
        f"/api/conversation-threads/{thread['thread_id']}/messages",
        json={"content": "主角要是那种克制但危险的人，平时忍着，关键时刻会立刻动手。"},
    )
    client.post(
        f"/api/conversation-threads/{thread['thread_id']}/messages",
        json={"content": "我希望前期更偏阴谋和压迫感推进，而不是纯升级刷图。"},
    )

    split = client.post(f"/api/conversation-threads/{thread['thread_id']}/split-stage-summary")

    assert split.status_code == 201
    decisions = split.json()
    assert len(decisions) == 3
    types = {item["decision_type"] for item in decisions}
    assert "writer_playbook_rule" in types
    assert "character_note" in types
    assert "outline_constraint" in types
    assert all(item["payload"]["source"] == "stage_confirmation" for item in decisions)

    refreshed = client.get(f"/api/conversation-threads/{thread['thread_id']}").json()
    assert refreshed["interview_state"]["stage_confirmation"]["action_recommendation"]["mode"] == "apply_and_split"


def test_character_and_outline_rooms_expose_carry_over_context() -> None:
    client = make_client()
    project = client.post(
        "/api/projects",
        json={
            "name": "分流承接项目",
            "default_user_brief": {"title": "长夜炉火", "idea_seed": "一个被逐出山门的人，靠炉火中的古老声音翻盘。"},
            "default_target_chapters": 1,
        },
    ).json()

    bootstrap = client.post(
        f"/api/projects/{project['project_id']}/conversation-threads",
        json={"scope": "project_bootstrap"},
    ).json()
    for content in [
        "我最想保住的是压迫中翻盘和悬念感。",
        "主角要是那种克制但危险的人，平时忍着，关键时刻会立刻动手。",
        "我希望前期更偏阴谋和压迫感推进，而不是纯升级刷图。",
    ]:
        client.post(
            f"/api/conversation-threads/{bootstrap['thread_id']}/messages",
            json={"content": content},
        )
    client.post(f"/api/conversation-threads/{bootstrap['thread_id']}/apply-project-summary")
    client.post(f"/api/conversation-threads/{bootstrap['thread_id']}/split-stage-summary")

    character_thread = client.post(
        f"/api/projects/{project['project_id']}/conversation-threads",
        json={"scope": "character_room"},
    ).json()
    outline_thread = client.post(
        f"/api/projects/{project['project_id']}/conversation-threads",
        json={"scope": "outline_room"},
    ).json()

    character_context = character_thread["thread_context"]
    outline_context = outline_thread["thread_context"]

    assert character_context["title"] == "人物讨论承接说明"
    assert any("克制但危险" in item["summary"] for item in character_context["inherited_items"])
    assert "关键关系张力" in character_context["missing_items"]
    assert character_context["priority_item"] == "主角第一印象"
    assert "先把主角一出场给人的感觉定住" in character_context["priority_reason"]
    assert character_context["priority_options"][0] == "克制"

    assert outline_context["title"] == "大纲讨论承接说明"
    assert any("阴谋和压迫感推进" in item["summary"] for item in outline_context["inherited_items"])
    assert "卷末高潮" in outline_context["missing_items"]
    assert outline_context["priority_item"] == "第一卷主推动力"
    assert "先抓住第一卷主要靠什么把读者往下带" in outline_context["priority_reason"]
    assert outline_context["priority_options"][0] == "一层层升级"


def test_character_and_outline_stage_summaries_can_be_applied_to_project_brief() -> None:
    client = make_client()
    project = client.post(
        "/api/projects",
        json={
            "name": "阶段摘要写回项目",
            "default_user_brief": {"title": "长夜炉火", "idea_seed": "一个被逐出山门的人，靠炉火中的古老声音翻盘。"},
            "default_target_chapters": 1,
        },
    ).json()

    bootstrap = client.post(
        f"/api/projects/{project['project_id']}/conversation-threads",
        json={"scope": "project_bootstrap"},
    ).json()
    for content in [
        "我最想保住的是压迫中翻盘和悬念感。",
        "主角要是那种克制但危险的人，平时忍着，关键时刻会立刻动手。",
        "我希望前期更偏阴谋和压迫感推进，而不是纯升级刷图。",
    ]:
        client.post(
            f"/api/conversation-threads/{bootstrap['thread_id']}/messages",
            json={"content": content},
        )
    client.post(f"/api/conversation-threads/{bootstrap['thread_id']}/apply-stage-summary")
    client.post(f"/api/conversation-threads/{bootstrap['thread_id']}/split-stage-summary")

    character_thread = client.post(
        f"/api/projects/{project['project_id']}/conversation-threads",
        json={"scope": "character_room"},
    ).json()
    client.post(
        f"/api/conversation-threads/{character_thread['thread_id']}/messages",
        json={"content": "他真正想摆脱的是被宗门轻易决定命运的处境。"},
    )
    client.post(
        f"/api/conversation-threads/{character_thread['thread_id']}/messages",
        json={"content": "最关键的关系张力，是他和旧师门首席之间既互相防备又互相需要。"},
    )
    applied_character = client.post(f"/api/conversation-threads/{character_thread['thread_id']}/apply-stage-summary")
    assert applied_character.status_code == 200
    assert applied_character.json()["default_user_brief"]["character_summary"]["title"] == "人物设定摘要"

    outline_thread = client.post(
        f"/api/projects/{project['project_id']}/conversation-threads",
        json={"scope": "outline_room"},
    ).json()
    client.post(
        f"/api/conversation-threads/{outline_thread['thread_id']}/messages",
        json={"content": "第一卷主推动力是主角借宗门试炼追查自己被逐出的真相。"},
    )
    client.post(
        f"/api/conversation-threads/{outline_thread['thread_id']}/messages",
        json={"content": "中段最值得期待的变化，是主角发现自己一直在替真正幕后黑手扫尾。"},
    )
    applied_outline = client.post(f"/api/conversation-threads/{outline_thread['thread_id']}/apply-stage-summary")
    assert applied_outline.status_code == 200
    brief = applied_outline.json()["default_user_brief"]
    assert brief["outline_summary"]["title"] == "第一卷方向摘要"
    assert brief["outline_summary"]["source_scope"] == "outline_room"


def test_draft_recap_section_can_be_adopted_directly() -> None:
    app = create_app(
        config=AppConfig(
            stub_mode=True,
            openai_api_key=None,
            admin_token=None,
            database_url="sqlite:///:memory:",
            model_name="gpt-5-nano",
            project_id="api-test",
            operator_id="tester",
        ),
        store=InMemoryStore(),
    )

    class FakeWorkflow:
        def prepare_project_request(self, *, project, user_brief, target_chapters, operator_id, quick_mode=False):
            return {
                "user_brief": user_brief or project.default_user_brief,
                "target_chapters": target_chapters or project.default_target_chapters,
                "operator_id": operator_id or "tester",
                "quick_mode": quick_mode,
            }

        def run_project(self, *, project, request_payload, on_update=None):
            return {
                "current_card": {"chapter_no": 1, "purpose": "第1章章卡"},
                "publish_package": {"chapter_no": 1, "title": "第1章", "full_text": "正文"},
                "brief_snapshot": request_payload.get("user_brief"),
                "writer_playbook": request_payload.get("writer_playbook"),
                "feedback_summary": {"chapter_no": 1},
                "event_log": ["chapter_card_ready:1", "release_package_ready:1", "feedback_ingested:1"],
            }

    app.state.workflow = FakeWorkflow()
    client = TestClient(app)
    project = client.post(
        "/api/projects",
        json={
            "name": "草案直采项目",
            "default_user_brief": {"title": "长夜炉火", "idea_seed": "一个被逐出山门的人，靠炉火中的古老声音翻盘。"},
            "default_target_chapters": 1,
        },
    ).json()

    thread = client.post(
        f"/api/projects/{project['project_id']}/conversation-threads",
        json={"scope": "project_bootstrap"},
    ).json()
    direct = client.post(
        f"/api/conversation-threads/{thread['thread_id']}/decisions",
        json={
            "decision_type": "character_note",
            "content": "主角要是那种克制但危险的人，平时忍着，关键时刻会立刻动手。",
            "source_label": "当前理解草案 · 主角行动方式",
        },
    )

    assert direct.status_code == 201
    assert direct.json()["payload"]["source"] == "draft_recap"
    assert direct.json()["payload"]["source_label"] == "当前理解草案 · 主角行动方式"

    run_response = client.post(f"/api/projects/{project['project_id']}/runs", json={})
    assert run_response.status_code == 201
    request_payload = run_response.json()["request"]
    assert request_payload["conversation_guidance"]["character_note_count"] == 1
    assert "克制但危险" in request_payload["user_brief"]["character_notes"][0]


def test_conversation_decision_is_persisted_and_applied_to_run_request() -> None:
    app = create_app(
        config=AppConfig(
            stub_mode=True,
            openai_api_key=None,
            admin_token=None,
            database_url="sqlite:///:memory:",
            model_name="gpt-5-nano",
            project_id="api-test",
            operator_id="tester",
        ),
        store=InMemoryStore(),
    )

    class FakeWorkflow:
        def prepare_project_request(self, *, project, user_brief, target_chapters, operator_id, quick_mode=False):
            return {
                "user_brief": user_brief or project.default_user_brief,
                "target_chapters": target_chapters or project.default_target_chapters,
                "operator_id": operator_id or "tester",
                "quick_mode": quick_mode,
            }

        def run_project(self, *, project, request_payload, on_update=None):
            return {
                "current_card": {"chapter_no": 1, "purpose": "第1章章卡"},
                "publish_package": {"chapter_no": 1, "title": "第1章", "full_text": "正文"},
                "writer_playbook": request_payload.get("writer_playbook"),
                "feedback_summary": {"chapter_no": 1},
                "event_log": ["chapter_card_ready:1", "release_package_ready:1", "feedback_ingested:1"],
            }

    app.state.workflow = FakeWorkflow()
    client = TestClient(app)
    project = client.post(
        "/api/projects",
        json={"name": "对话采纳项目", "default_user_brief": {"title": "长夜炉火"}, "default_target_chapters": 1},
    ).json()

    thread = client.post(
        f"/api/projects/{project['project_id']}/conversation-threads",
        json={"scope": "project_bootstrap"},
    ).json()
    created_messages = client.post(
        f"/api/conversation-threads/{thread['thread_id']}/messages",
        json={"content": "主角的主动动作要在前半章出现。"},
    ).json()
    adopted = client.post(
        f"/api/conversation-messages/{created_messages[0]['message_id']}/adopt",
        json={"decision_type": "writer_playbook_rule"},
    )

    assert adopted.status_code == 201
    decisions = client.get(f"/api/projects/{project['project_id']}/conversation-decisions")
    assert decisions.status_code == 200
    assert decisions.json()[0]["decision_type"] == "writer_playbook_rule"

    run_response = client.post(f"/api/projects/{project['project_id']}/runs", json={})
    assert run_response.status_code == 201
    assert run_response.json()["request"]["conversation_guidance"]["decision_count"] == 1
    completed = wait_for_run(client, run_response.json()["run_id"])
    assert "主角的主动动作要在前半章出现。" in completed["result"]["writer_playbook"]["always_apply"]


def test_structured_conversation_decisions_are_merged_into_user_brief() -> None:
    app = create_app(
        config=AppConfig(
            stub_mode=True,
            openai_api_key=None,
            admin_token=None,
            database_url="sqlite:///:memory:",
            model_name="gpt-5-nano",
            project_id="api-test",
            operator_id="tester",
        ),
        store=InMemoryStore(),
    )

    class FakeWorkflow:
        def prepare_project_request(self, *, project, user_brief, target_chapters, operator_id, quick_mode=False):
            return {
                "user_brief": user_brief or project.default_user_brief,
                "target_chapters": target_chapters or project.default_target_chapters,
                "operator_id": operator_id or "tester",
                "quick_mode": quick_mode,
            }

        def run_project(self, *, project, request_payload, on_update=None):
            return {
                "current_card": {"chapter_no": 1, "purpose": "第1章章卡"},
                "publish_package": {"chapter_no": 1, "title": "第1章", "full_text": "正文"},
                "feedback_summary": {"chapter_no": 1},
                "brief_snapshot": request_payload.get("user_brief"),
                "event_log": ["chapter_card_ready:1", "release_package_ready:1", "feedback_ingested:1"],
            }

    app.state.workflow = FakeWorkflow()
    client = TestClient(app)
    project = client.post(
        "/api/projects",
        json={"name": "结构化对话项目", "default_user_brief": {"title": "长夜炉火"}, "default_target_chapters": 1},
    ).json()

    character_thread = client.post(
        f"/api/projects/{project['project_id']}/conversation-threads",
        json={"scope": "character_room"},
    ).json()
    character_messages = client.post(
        f"/api/conversation-threads/{character_thread['thread_id']}/messages",
        json={"content": "主角外冷内烈，平时克制，但遇到底线问题会立刻出手。"},
    ).json()
    adopt_character = client.post(
        f"/api/conversation-messages/{character_messages[0]['message_id']}/adopt",
        json={"decision_type": "character_note"},
    )
    assert adopt_character.status_code == 201

    outline_thread = client.post(
        f"/api/projects/{project['project_id']}/conversation-threads",
        json={"scope": "outline_room"},
    ).json()
    outline_messages = client.post(
        f"/api/conversation-threads/{outline_thread['thread_id']}/messages",
        json={"content": "第一卷必须先立住师门压迫，再逐步揭开逐出真相，卷末要给出一次身份反转。"},
    ).json()
    adopt_outline = client.post(
        f"/api/conversation-messages/{outline_messages[0]['message_id']}/adopt",
        json={"decision_type": "outline_constraint"},
    )
    assert adopt_outline.status_code == 201

    run_response = client.post(f"/api/projects/{project['project_id']}/runs", json={})

    assert run_response.status_code == 201
    request_payload = run_response.json()["request"]
    assert request_payload["conversation_guidance"]["character_note_count"] == 1
    assert request_payload["conversation_guidance"]["outline_constraint_count"] == 1
    assert "主角外冷内烈" in request_payload["user_brief"]["character_notes"][0]
    assert "第一卷必须先立住师门压迫" in request_payload["user_brief"]["outline_notes"][0]

    completed = wait_for_run(client, run_response.json()["run_id"])
    assert "character_notes" in completed["result"]["brief_snapshot"]
    assert "outline_notes" in completed["result"]["brief_snapshot"]


def test_conversation_decision_can_be_updated_and_deleted() -> None:
    app = create_app(
        config=AppConfig(
            stub_mode=True,
            openai_api_key=None,
            admin_token=None,
            database_url="sqlite:///:memory:",
            model_name="gpt-5-nano",
            project_id="api-test",
            operator_id="tester",
        ),
        store=InMemoryStore(),
    )

    class FakeWorkflow:
        def prepare_project_request(self, *, project, user_brief, target_chapters, operator_id, quick_mode=False):
            return {
                "user_brief": user_brief or project.default_user_brief,
                "target_chapters": target_chapters or project.default_target_chapters,
                "operator_id": operator_id or "tester",
                "quick_mode": quick_mode,
            }

        def run_project(self, *, project, request_payload, on_update=None):
            return {
                "current_card": {"chapter_no": 1, "purpose": "第1章章卡"},
                "publish_package": {"chapter_no": 1, "title": "第1章", "full_text": "正文"},
                "writer_playbook": request_payload.get("writer_playbook"),
                "feedback_summary": {"chapter_no": 1},
                "event_log": ["chapter_card_ready:1", "release_package_ready:1", "feedback_ingested:1"],
            }

    app.state.workflow = FakeWorkflow()
    client = TestClient(app)
    project = client.post(
        "/api/projects",
        json={"name": "更新采纳项目", "default_user_brief": {"title": "长夜炉火"}, "default_target_chapters": 1},
    ).json()

    thread = client.post(
        f"/api/projects/{project['project_id']}/conversation-threads",
        json={"scope": "project_bootstrap"},
    ).json()
    created_messages = client.post(
        f"/api/conversation-threads/{thread['thread_id']}/messages",
        json={"content": "主角的主动动作要在前半章出现。"},
    ).json()
    decision = client.post(
        f"/api/conversation-messages/{created_messages[0]['message_id']}/adopt",
        json={"decision_type": "writer_playbook_rule"},
    ).json()

    updated = client.patch(
        f"/api/conversation-decisions/{decision['decision_id']}",
        json={"content": "主角的主动动作要在前600字出现。"},
    )
    assert updated.status_code == 200
    assert updated.json()["payload"]["rule"] == "主角的主动动作要在前600字出现。"

    run_response = client.post(f"/api/projects/{project['project_id']}/runs", json={})
    completed = wait_for_run(client, run_response.json()["run_id"])
    assert "主角的主动动作要在前600字出现。" in completed["result"]["writer_playbook"]["always_apply"]

    deleted = client.delete(f"/api/conversation-decisions/{decision['decision_id']}")
    assert deleted.status_code == 204

    run_response_after_delete = client.post(
        f"/api/projects/{project['project_id']}/runs",
        json={"target_chapters": 1},
    )
    assert run_response_after_delete.status_code == 201
    assert run_response_after_delete.json()["request"]["conversation_guidance"] is None


def test_chapter_planning_thread_exposes_write_before_context() -> None:
    app = create_app(
        config=AppConfig(
            stub_mode=True,
            openai_api_key=None,
            admin_token=None,
            database_url="sqlite:///:memory:",
            model_name="gpt-5-nano",
            project_id="api-test",
            operator_id="tester",
        ),
        store=InMemoryStore(),
    )

    class FakeWorkflow:
        def prepare_project_request(self, *, project, user_brief, target_chapters, operator_id, quick_mode=False):
            return {
                "user_brief": user_brief or project.default_user_brief,
                "target_chapters": target_chapters or project.default_target_chapters,
                "operator_id": operator_id or "tester",
                "quick_mode": quick_mode,
            }

        def run_project(self, *, project, request_payload, on_update=None):
            return {
                "planning_context": {
                    "chapter_no": 1,
                    "applied_guardrails": ["主角必须在前半章先行动一次"],
                    "issue_applications": [
                        {
                            "issue_id": "iss_1",
                            "fix_instruction": "把关键冲突前置到前半章",
                            "applied_guardrail": "提前规避已知问题：把关键冲突前置到前半章",
                        }
                    ],
                },
                "current_card": {
                    "chapter_no": 1,
                    "purpose": "让主角第一次主动试探敌方底牌",
                    "pov": "third_limited_mc",
                    "must_include": ["一次明确试探", "章末风险升级"],
                    "must_not_change": ["主角尚未暴露底牌"],
                },
                "issue_ledger": {
                    "issues": [
                        {
                            "issue_id": "iss_1",
                            "status": "open",
                            "fix_instruction": "把关键冲突前置到前半章",
                        }
                    ]
                },
                "publish_package": {"chapter_no": 1, "title": "第1章", "full_text": "正文"},
                "feedback_summary": {"chapter_no": 1},
                "event_log": ["chapter_card_ready:1", "release_package_ready:1", "feedback_ingested:1"],
            }

    app.state.workflow = FakeWorkflow()
    client = TestClient(app)
    project = client.post(
        "/api/projects",
        json={"name": "章卡协商项目", "default_user_brief": {"title": "长夜炉火"}, "default_target_chapters": 1},
    ).json()

    run_response = client.post(f"/api/projects/{project['project_id']}/runs", json={})
    assert run_response.status_code == 201
    completed = wait_for_run(client, run_response.json()["run_id"])
    assert completed["status"] == "completed"

    thread_response = client.post(
        f"/api/projects/{project['project_id']}/conversation-threads",
        json={
            "scope": "chapter_planning",
            "linked_run_id": completed["run_id"],
            "linked_chapter_no": 1,
        },
    )
    assert thread_response.status_code == 201
    thread = thread_response.json()
    assert thread["thread_context"]["chapter_no"] == 1
    assert thread["thread_context"]["purpose"] == "让主角第一次主动试探敌方底牌"
    assert thread["thread_context"]["must_include"][0] == "一次明确试探"
    assert thread["thread_context"]["pending_issues"][0] == "把关键冲突前置到前半章"
    assert thread["thread_context"]["patch_count"] == 0


def test_human_check_creates_checkpoint_thread_and_approval() -> None:
    app = create_app(
        config=AppConfig(
            stub_mode=True,
            openai_api_key=None,
            admin_token=None,
            database_url="sqlite:///:memory:",
            model_name="gpt-5-nano",
            project_id="api-test",
            operator_id="tester",
        ),
        store=InMemoryStore(),
    )

    class FakeWorkflow:
        def prepare_project_request(self, *, project, user_brief, target_chapters, operator_id, quick_mode=False):
            return {
                "user_brief": user_brief or project.default_user_brief,
                "target_chapters": target_chapters or project.default_target_chapters,
                "operator_id": operator_id or "tester",
                "quick_mode": quick_mode,
            }

        def run_project(self, *, project, request_payload, on_update=None):
            return {
                "current_card": {"chapter_no": 1, "purpose": "第1章章卡"},
                "phase_decision": {
                    "final_decision": "human_check",
                    "reason": "同类 major 问题连续复发，需要人工决定先改章卡还是正文。",
                },
                "human_guidance": {
                    "chapter_no": 1,
                    "reason": "同类 major 问题连续复发，需要人工决定先改章卡还是正文。",
                    "must_fix": ["先决定冲突前置还是重写正文开头"],
                    "suggested_actions": ["continue", "rewrite", "replan"],
                    "issue_progress_summary": "已解决 0 项，复发 1 项，新增 0 项。",
                    "stubborn_issues": [
                        {
                            "issue_id": "iss_1",
                            "fix_instruction": "把关键冲突前置到前半章",
                            "evidence": "前半章推进过慢",
                        }
                    ],
                },
                "issue_ledger": {
                    "chapter_no": 1,
                    "status": "needs_human_review",
                    "progress_summary": "已解决 0 项，复发 1 项，新增 0 项。",
                    "issues": [
                        {
                            "issue_id": "iss_1",
                            "status": "recurring",
                            "attempts": 2,
                            "severity": "major",
                            "fix_instruction": "把关键冲突前置到前半章",
                            "evidence": "前半章推进过慢",
                        }
                    ],
                },
                "blockers": ["需要人工审核或继续指令。"],
                "event_log": ["phase_decision:human_check", "human_gate_reached"],
            }

    app.state.workflow = FakeWorkflow()
    client = TestClient(app)
    project = client.post(
        "/api/projects",
        json={"name": "人工检查点项目", "default_user_brief": {"title": "长夜炉火"}, "default_target_chapters": 1},
    ).json()

    run_response = client.post(f"/api/projects/{project['project_id']}/runs", json={})
    assert run_response.status_code == 201
    completed = wait_for_run(client, run_response.json()["run_id"])
    assert completed["status"] == "awaiting_approval"
    checkpoint = completed["result"]["human_checkpoint"]
    assert checkpoint["status"] == "paused_for_human"
    assert checkpoint["approval_id"]
    assert checkpoint["thread_id"]

    approvals = client.get(f"/api/projects/{project['project_id']}/approval-requests")
    assert approvals.status_code == 200
    assert len(approvals.json()) == 1
    assert approvals.json()[0]["approval_id"] == checkpoint["approval_id"]

    threads = client.get(f"/api/projects/{project['project_id']}/conversation-threads")
    assert threads.status_code == 200
    intervention_threads = [item for item in threads.json() if item["scope"] == "rewrite_intervention"]
    assert len(intervention_threads) == 1
    assert intervention_threads[0]["thread_id"] == checkpoint["thread_id"]
    assert intervention_threads[0]["linked_run_id"] == completed["run_id"]
    assert intervention_threads[0]["thread_context"]["checkpoint_reason"].startswith("同类 major 问题连续复发")


def test_run_flow() -> None:
    client = make_client()
    project = client.post(
        "/api/projects",
        json={
            "name": "测试项目",
            "default_user_brief": {
                "title": "长夜炉火",
                "genre": "东方玄幻",
                "platform": "起点中文网",
                "hook": "一个被逐出山门的外门弟子，靠偷听禁地炉火中的古老对话逆天改命。",
                "must_have": ["稳步升级", "师门阴谋", "章末钩子强"],
                "must_not_have": ["后宫泛滥", "无代价外挂"],
            },
            "default_target_chapters": 2,
        },
    ).json()

    run_response = client.post(f"/api/projects/{project['project_id']}/runs", json={})

    assert run_response.status_code == 201
    run_payload = run_response.json()
    assert run_payload["status"] == "running"
    assert run_payload["finished_at"] is None
    completed_run = wait_for_run(client, run_payload["run_id"])
    assert completed_run["status"] == "completed"
    assert completed_run["finished_at"] is not None
    assert completed_run["result"]["publish_package"]["chapter_no"] == 2
    assert completed_run["artifact_count"] > 0
    assert completed_run["has_artifacts"] is True

    get_run_response = client.get(f"/api/runs/{run_payload['run_id']}")

    assert get_run_response.status_code == 200
    assert get_run_response.json()["run_id"] == run_payload["run_id"]

    chapters_response = client.get(f"/api/projects/{project['project_id']}/chapters")
    runs_response = client.get(f"/api/projects/{project['project_id']}/runs")
    artifacts_response = client.get(f"/api/runs/{run_payload['run_id']}/artifacts")

    assert chapters_response.status_code == 200
    assert chapters_response.json()[0]["chapter_no"] == 2
    assert runs_response.status_code == 200
    assert runs_response.json()[0]["run_id"] == run_payload["run_id"]
    assert runs_response.json()[0]["artifact_count"] > 0
    assert artifacts_response.status_code == 200
    assert any(item["artifact_type"] == "publish_package" for item in artifacts_response.json())


def test_create_run_continues_latest_completed_chapter() -> None:
    app = create_app(
        config=AppConfig(
            stub_mode=True,
            openai_api_key=None,
            admin_token=None,
            database_url="sqlite:///:memory:",
            model_name="gpt-5-nano",
            project_id="api-test",
            operator_id="tester",
        ),
        store=InMemoryStore(),
    )

    class FakeWorkflow:
        def prepare_project_request(self, *, project, user_brief, target_chapters, operator_id, quick_mode=False):
            return {
                "user_brief": user_brief or project.default_user_brief,
                "target_chapters": target_chapters or project.default_target_chapters,
                "operator_id": operator_id or "tester",
                "quick_mode": quick_mode,
            }

        def prepare_continuation_request(self, *, project, original_request, artifacts, operator_id):
            service = WorkflowService(
                AppConfig(
                    stub_mode=True,
                    openai_api_key=None,
                    admin_token=None,
                    database_url="sqlite:///:memory:",
                    model_name="gpt-5-nano",
                    project_id="api-test",
                    operator_id="tester",
                )
            )
            return service.prepare_continuation_request(
                project=project,
                original_request=original_request,
                artifacts=artifacts,
                operator_id=operator_id,
            )

        def run_project(self, *, project, request_payload, on_update=None):
            raise AssertionError("expected continuation path, not fresh run")

        def run_followup(self, *, project, request_payload, on_update=None):
            return {
                "current_card": {"chapter_no": 2, "purpose": "第2章章卡"},
                "publish_package": {"chapter_no": 2, "title": "第2章", "full_text": "正文"},
                "canon_state": {"story_clock": {"current_chapter": 2}},
                "feedback_summary": {"chapter_no": 2},
                "event_log": ["chapter_card_ready:2", "release_package_ready:2", "feedback_ingested:2"],
            }

    app.state.workflow = FakeWorkflow()
    client = TestClient(app)

    project = client.post(
        "/api/projects",
        json={"name": "续写测试", "default_user_brief": {"title": "测试"}, "default_target_chapters": 1},
    ).json()
    source_run = app.state.store.save_run(
        project_id=project["project_id"],
        status="completed",
        request={"user_brief": {"title": "测试"}, "target_chapters": 1, "operator_id": "tester"},
        result={
            "publish_package": {"chapter_no": 1, "title": "第1章", "full_text": "正文"},
            "feedback_summary": {"chapter_no": 1},
            "canon_state": {"story_clock": {"current_chapter": 1}},
        },
        error=None,
    )
    app.state.store.save_run_outputs(
        run=source_run,
        result={
            "publish_package": {"chapter_no": 1, "title": "第1章", "full_text": "正文"},
            "feedback_summary": {"chapter_no": 1},
            "canon_state": {"story_clock": {"current_chapter": 1}},
        },
    )

    run_response = client.post(f"/api/projects/{project['project_id']}/runs", json={"operator_id": "editor-1"})

    assert run_response.status_code == 201
    payload = run_response.json()
    assert payload["request"]["target_chapters"] == 2
    stored_run = app.state.store.get_run(payload["run_id"])
    assert stored_run is not None
    assert stored_run.request["chapters_completed"] == 1

    completed = wait_for_run(client, payload["run_id"])
    assert completed["result"]["publish_package"]["chapter_no"] == 2


def test_quick_mode_run_request_is_persisted() -> None:
    client = make_client()
    project = client.post(
        "/api/projects",
        json={
            "name": "快速试写项目",
            "default_user_brief": {
                "title": "长夜炉火",
                "genre": "东方玄幻",
            },
            "default_target_chapters": 1,
        },
    ).json()

    run_response = client.post(
        f"/api/projects/{project['project_id']}/runs",
        json={"quick_mode": True, "operator_id": "quick-editor"},
    )

    assert run_response.status_code == 201
    payload = run_response.json()
    assert payload["request"]["quick_mode"] is True
    assert payload["request"]["human_instruction"]["requested_action"] == "quick_trial"


def test_formal_launch_note_is_persisted() -> None:
    client = make_client()
    project = client.post(
        "/api/projects",
        json={
            "name": "正式开书项目",
            "default_user_brief": {
                "title": "长夜炉火",
                "genre": "东方玄幻",
            },
            "default_target_chapters": 1,
        },
    ).json()

    run_response = client.post(
        f"/api/projects/{project['project_id']}/runs",
        json={
            "operator_id": "editor-1",
            "chapter_focus": "先把主角立住",
            "launch_note": "先把主角受困和第一次反击写扎实。",
        },
    )

    assert run_response.status_code == 201
    payload = run_response.json()
    assert payload["request"]["human_instruction"]["requested_action"] == "formal_launch"
    assert payload["request"]["human_instruction"]["payload"]["chapter_focus"] == "先把主角立住"
    assert payload["request"]["human_instruction"]["payload"]["launch_note"] == "先把主角受困和第一次反击写扎实。"


def test_approval_request_flow() -> None:
    client = make_client()
    project = client.post(
        "/api/projects",
        json={
            "name": "测试项目",
            "default_user_brief": {
                "title": "长夜炉火",
                "genre": "东方玄幻",
                "platform": "起点中文网",
                "hook": "一个被逐出山门的外门弟子，靠偷听禁地炉火中的古老对话逆天改命。",
                "must_have": ["稳步升级", "师门阴谋", "章末钩子强"],
                "must_not_have": ["后宫泛滥", "无代价外挂"],
            },
            "default_target_chapters": 1,
        },
    ).json()
    run_payload = client.post(f"/api/projects/{project['project_id']}/runs", json={}).json()
    wait_for_run(client, run_payload["run_id"])

    create_response = client.post(
        f"/api/runs/{run_payload['run_id']}/approval-requests",
        json={
            "requested_action": "continue",
            "reason": "需要人工确认是否继续写下一章",
            "chapter_no": 1,
            "payload": {"source": "test-suite"},
        },
    )

    assert create_response.status_code == 201
    approval_id = create_response.json()["approval_id"]

    resolve_response = client.post(
        f"/api/approval-requests/{approval_id}/resolve",
        json={
            "decision": "approved",
            "operator_id": "editor-1",
            "comment": "继续",
        },
    )

    assert resolve_response.status_code == 200
    assert resolve_response.json()["status"] == "approved"
    list_response = client.get(f"/api/projects/{project['project_id']}/approval-requests")
    assert list_response.status_code == 200
    assert list_response.json()[0]["approval_id"] == approval_id


def test_execute_approved_followup_run_continues_to_next_chapter() -> None:
    client = make_client()
    project = client.post(
        "/api/projects",
        json={
            "name": "测试项目",
            "default_user_brief": {
                "title": "长夜炉火",
                "genre": "东方玄幻",
                "platform": "起点中文网",
                "hook": "一个被逐出山门的外门弟子，靠偷听禁地炉火中的古老对话逆天改命。",
                "must_have": ["稳步升级", "师门阴谋", "章末钩子强"],
                "must_not_have": ["后宫泛滥", "无代价外挂"],
            },
            "default_target_chapters": 1,
        },
    ).json()
    initial_run = client.post(f"/api/projects/{project['project_id']}/runs", json={}).json()
    wait_for_run(client, initial_run["run_id"])

    approval = client.post(
        f"/api/runs/{initial_run['run_id']}/approval-requests",
        json={
            "requested_action": "continue",
            "reason": "继续下一章",
            "chapter_no": 1,
            "payload": {"source": "test-suite"},
        },
    ).json()
    client.post(
        f"/api/approval-requests/{approval['approval_id']}/resolve",
        json={"decision": "approved", "operator_id": "editor-1", "comment": "延续当前悬念，但把主角主动试探前置"},
    )

    execute_response = client.post(f"/api/approval-requests/{approval['approval_id']}/execute")

    assert execute_response.status_code == 200
    execute_payload = execute_response.json()
    assert execute_payload["run"]["status"] == "running"
    assert execute_payload["run"]["finished_at"] is None
    completed_followup = wait_for_run(client, execute_payload["run"]["run_id"])
    assert completed_followup["finished_at"] is not None
    assert completed_followup["result"]["publish_package"]["chapter_no"] == 2
    assert execute_payload["approval"]["executed_run_id"] == execute_payload["run"]["run_id"]
    assert completed_followup["request"]["human_instruction"]["comment"] == "延续当前悬念，但把主角主动试探前置"


def test_execute_approved_followup_run_respects_recovery_override() -> None:
    app = create_app(
        config=AppConfig(
            stub_mode=True,
            openai_api_key=None,
            admin_token=None,
            database_url="sqlite:///:memory:",
            model_name="gpt-5-nano",
            project_id="api-test",
            operator_id="tester",
        ),
        store=InMemoryStore(),
    )

    class FakeWorkflow:
        def prepare_project_request(self, *, project, user_brief, target_chapters, operator_id, quick_mode=False):
            return {
                "user_brief": user_brief or project.default_user_brief,
                "target_chapters": target_chapters or project.default_target_chapters,
                "operator_id": operator_id or "tester",
                "quick_mode": quick_mode,
                "human_instruction": None,
            }

        def prepare_followup_request(self, *, project, original_request, artifacts, approval, requested_action):
            service = WorkflowService(
                AppConfig(
                    stub_mode=True,
                    openai_api_key=None,
                    admin_token=None,
                    database_url="sqlite:///:memory:",
                    model_name="gpt-5-nano",
                    project_id="api-test",
                    operator_id="tester",
                )
            )
            return service.prepare_followup_request(
                project=project,
                original_request=original_request,
                artifacts=artifacts,
                approval=approval,
                requested_action=requested_action,
            )

        def run_followup(self, *, project, request_payload, on_update=None):
            chapter_no = request_payload["target_chapters"]
            return {
                "current_card": {"chapter_no": chapter_no, "purpose": f"第{chapter_no}章章卡"},
                "publish_package": {"chapter_no": chapter_no, "title": f"第{chapter_no}章", "full_text": "正文"},
                "canon_state": {"story_clock": {"current_chapter": chapter_no}},
                "feedback_summary": {"chapter_no": chapter_no},
                "event_log": [f"chapter_card_ready:{chapter_no}", f"release_package_ready:{chapter_no}", f"feedback_ingested:{chapter_no}"],
            }

    app.state.workflow = FakeWorkflow()
    client = TestClient(app)

    project = client.post(
        "/api/projects",
        json={"name": "恢复路径覆盖", "default_user_brief": {"title": "测试"}, "default_target_chapters": 1},
    ).json()
    source_run = app.state.store.save_run(
        project_id=project["project_id"],
        status="completed",
        request={"user_brief": {"title": "测试"}, "target_chapters": 1, "operator_id": "tester"},
        result={
            "current_card": {"chapter_no": 1, "purpose": "第1章章卡"},
            "publish_package": {"chapter_no": 1, "title": "第1章", "full_text": "正文"},
            "canon_state": {"story_clock": {"current_chapter": 1}},
            "feedback_summary": {"chapter_no": 1},
        },
        error=None,
    )
    app.state.store.save_run_outputs(
        run=source_run,
        result={
            "current_card": {"chapter_no": 1, "purpose": "第1章章卡"},
            "publish_package": {"chapter_no": 1, "title": "第1章", "full_text": "正文"},
            "canon_state": {"story_clock": {"current_chapter": 1}},
            "feedback_summary": {"chapter_no": 1},
            "event_log": ["release_package_ready:1", "feedback_ingested:1"],
        },
    )
    approval = app.state.store.create_approval_request(
        project_id=project["project_id"],
        run_id=source_run.run_id,
        chapter_no=1,
        requested_action="continue",
        reason="默认是继续，但这次改为重做章卡",
        payload={"source": "test"},
    )
    app.state.store.resolve_approval_request(
        approval_id=approval.approval_id,
        decision="approved",
        operator_id="editor-1",
        comment="先重做章卡，再重写同章",
    )

    execute_response = client.post(
        f"/api/approval-requests/{approval.approval_id}/execute",
        json={"requested_action_override": "replan"},
    )

    assert execute_response.status_code == 200
    payload = execute_response.json()
    assert payload["run"]["request"]["target_chapters"] == 1
    assert payload["run"]["request"]["human_instruction"]["requested_action"] == "replan"
    assert payload["run"]["request"]["human_instruction"]["payload"]["executed_requested_action"] == "replan"
    stored_run = app.state.store.get_run(payload["run"]["run_id"])
    assert stored_run is not None
    assert stored_run.request["chapters_completed"] == 0


def test_execute_approved_followup_from_human_check_continues_next_chapter() -> None:
    app = create_app(
        config=AppConfig(
            stub_mode=True,
            openai_api_key=None,
            admin_token=None,
            database_url="sqlite:///:memory:",
            model_name="gpt-5-nano",
            project_id="api-test",
            operator_id="tester",
        ),
        store=InMemoryStore(),
    )

    class FakeWorkflow:
        def prepare_project_request(self, *, project, user_brief, target_chapters, operator_id, quick_mode=False):
            return {
                "user_brief": user_brief or project.default_user_brief,
                "target_chapters": target_chapters or project.default_target_chapters,
                "operator_id": operator_id or "tester",
                "quick_mode": quick_mode,
                "human_instruction": None,
            }

        def prepare_followup_request(self, *, project, original_request, artifacts, approval, requested_action):
            service = WorkflowService(
                AppConfig(
                    stub_mode=True,
                    openai_api_key=None,
                    admin_token=None,
                    database_url="sqlite:///:memory:",
                    model_name="gpt-5-nano",
                    project_id="api-test",
                    operator_id="tester",
                )
            )
            return service.prepare_followup_request(
                project=project,
                original_request=original_request,
                artifacts=artifacts,
                approval=approval,
                requested_action=requested_action,
            )

        def run_followup(self, *, project, request_payload, on_update=None):
            return {
                "current_card": {"chapter_no": 2, "purpose": "第2章章卡"},
                "publish_package": {"chapter_no": 2, "title": "第2章", "full_text": "正文"},
                "canon_state": {"story_clock": {"current_chapter": 2}},
                "feedback_summary": {"chapter_no": 2},
                "event_log": ["chapter_card_ready:2", "release_package_ready:2", "feedback_ingested:2"],
            }

    app.state.workflow = FakeWorkflow()
    client = TestClient(app)

    project = client.post(
        "/api/projects",
        json={"name": "人工审批续写", "default_user_brief": {"title": "测试"}, "default_target_chapters": 1},
    ).json()
    source_run = app.state.store.save_run(
        project_id=project["project_id"],
        status="awaiting_approval",
        request={"user_brief": {"title": "测试"}, "target_chapters": 1, "operator_id": "tester"},
        result={
            "current_card": {"chapter_no": 1, "purpose": "第1章章卡"},
            "phase_decision": {"final_decision": "human_check"},
            "event_log": ["chapter_card_ready:1", "phase_decision:human_check"],
        },
        error=None,
    )
    app.state.store.save_run_outputs(
        run=source_run,
        result={
            "current_card": {"chapter_no": 1, "purpose": "第1章章卡"},
            "canon_state": {"story_clock": {"current_arc": 1, "current_chapter": 0}},
            "phase_decision": {"final_decision": "human_check"},
            "human_guidance": {"chapter_no": 1},
            "event_log": ["chapter_card_ready:1", "phase_decision:human_check"],
        },
    )
    approval = app.state.store.create_approval_request(
        project_id=project["project_id"],
        run_id=source_run.run_id,
        chapter_no=1,
        requested_action="continue",
        reason="人工确认后继续下一章",
        payload={"source": "test"},
    )
    app.state.store.resolve_approval_request(
        approval_id=approval.approval_id,
        decision="approved",
        operator_id="editor-1",
        comment="继续下一章",
    )

    execute_response = client.post(f"/api/approval-requests/{approval.approval_id}/execute")

    assert execute_response.status_code == 200
    payload = execute_response.json()
    assert payload["run"]["request"]["target_chapters"] == 2
    stored_run = app.state.store.get_run(payload["run"]["run_id"])
    assert stored_run is not None
    assert stored_run.request["chapters_completed"] == 1

    completed = wait_for_run(client, payload["run"]["run_id"])
    assert completed["result"]["publish_package"]["chapter_no"] == 2


def test_admin_page_routes() -> None:
    client = make_client()

    root_response = client.get("/")
    admin_response = client.get("/admin")

    assert root_response.status_code == 200
    assert admin_response.status_code == 200
    assert "NovelStudio Admin" in root_response.text
    assert "NovelStudio Admin" in admin_response.text


def test_running_run_exposes_live_artifacts() -> None:
    app = create_app(
        config=AppConfig(
            stub_mode=True,
            openai_api_key=None,
            admin_token=None,
            database_url="sqlite:///:memory:",
            model_name="gpt-5-nano",
            project_id="api-test",
            operator_id="tester",
        ),
        store=InMemoryStore(),
    )
    release_run = Event()

    class FakeWorkflow:
        def prepare_project_request(self, *, project, user_brief, target_chapters, operator_id, quick_mode=False):
            return {
                "user_brief": user_brief or project.default_user_brief,
                "target_chapters": target_chapters or project.default_target_chapters,
                "operator_id": operator_id or "tester",
                "quick_mode": quick_mode,
                "human_instruction": None,
            }

        def run_project(self, *, project, request_payload, on_update=None):
            state = {
                "creative_contract": {"working_title": "测试标题"},
                "story_bible": {"premise": "测试世界"},
                "current_card": {"chapter_no": 1, "purpose": "测试章卡"},
                "phase_decision": {"final_decision": "rewrite"},
                "event_log": ["creative_contract_ready", "chapter_card_ready:1"],
                "rewrite_count": 0,
            }
            if on_update is not None:
                on_update("chapter_planner", state)
            release_run.wait(timeout=2)
            return {
                **state,
                "current_draft": {"title": "第1章", "content": "正文"},
                "publish_package": {"chapter_no": 1, "title": "第1章", "full_text": "正文"},
                "canon_state": {"story_clock": {"current_chapter": 1}},
                "feedback_summary": {"chapter_no": 1},
                "latest_review_reports": [],
            }

    app.state.workflow = FakeWorkflow()
    client = TestClient(app)

    project = client.post(
        "/api/projects",
        json={
            "name": "实时工件测试",
            "default_user_brief": {"title": "测试"},
            "default_target_chapters": 1,
        },
    ).json()

    run = client.post(f"/api/projects/{project['project_id']}/runs", json={}).json()

    deadline = time.time() + 2
    live_artifacts = []
    while time.time() < deadline:
        live_artifacts = client.get(f"/api/runs/{run['run_id']}/artifacts").json()
        if any(item["artifact_type"] == "current_card" for item in live_artifacts):
            break
        time.sleep(0.02)

    assert any(item["artifact_type"] == "creative_contract" for item in live_artifacts)
    assert any(item["artifact_type"] == "current_card" for item in live_artifacts)
    assert any(item["artifact_type"] == "phase_decision" for item in live_artifacts)
    run_snapshot = client.get(f"/api/runs/{run['run_id']}").json()
    assert run_snapshot["artifact_count"] >= 3
    assert run_snapshot["has_artifacts"] is True
    assert run_snapshot["result"]["progress"]["review_progress"]["total_count"] == 4

    release_run.set()
    completed_run = wait_for_run(client, run["run_id"])
    assert completed_run["status"] == "completed"


def test_running_run_exposes_parallel_reviewer_progress() -> None:
    app = create_app(
        config=AppConfig(
            stub_mode=True,
            openai_api_key=None,
            admin_token=None,
            database_url="sqlite:///:memory:",
            model_name="gpt-5-nano",
            project_id="api-test",
            operator_id="tester",
        ),
        store=InMemoryStore(),
    )
    release_run = Event()

    class FakeWorkflow:
        def prepare_project_request(self, *, project, user_brief, target_chapters, operator_id, quick_mode=False):
            return {
                "user_brief": user_brief or project.default_user_brief,
                "target_chapters": target_chapters or project.default_target_chapters,
                "operator_id": operator_id or "tester",
                "quick_mode": quick_mode,
                "human_instruction": None,
            }

        def run_project(self, *, project, request_payload, on_update=None):
            base_state = {
                "current_card": {"chapter_no": 1, "purpose": "测试章卡"},
                "event_log": ["chapter_draft_ready"],
                "rewrite_count": 0,
            }
            if on_update is not None:
                on_update("draft_writer", base_state)
                on_update(
                    "continuity_reviewer",
                    {
                        **base_state,
                        "review_reports": [
                            {
                                "reviewer": "continuity",
                                "decision": "pass",
                                "scores": {"continuity": 90, "pacing": 80, "style": 80, "hook": 80, "total": 83},
                                "hard_violations": [],
                                "issues": [],
                            }
                        ],
                        "event_log": ["chapter_draft_ready", "review_ready:continuity:pass"],
                    },
                )
                on_update(
                    "pacing_reviewer",
                    {
                        **base_state,
                        "review_reports": [
                            {
                                "reviewer": "continuity",
                                "decision": "pass",
                                "scores": {"continuity": 90, "pacing": 80, "style": 80, "hook": 80, "total": 83},
                                "hard_violations": [],
                                "issues": [],
                            },
                            {
                                "reviewer": "pacing",
                                "decision": "rewrite",
                                "scores": {"continuity": 82, "pacing": 72, "style": 80, "hook": 79, "total": 78},
                                "hard_violations": [],
                                "issues": [],
                            },
                        ],
                        "event_log": [
                            "chapter_draft_ready",
                            "review_ready:continuity:pass",
                            "review_ready:pacing:rewrite",
                        ],
                    },
                )
            release_run.wait(timeout=2)
            return {
                **base_state,
                "publish_package": {"chapter_no": 1, "title": "第1章", "full_text": "正文"},
                "latest_review_reports": [],
            }

    app.state.workflow = FakeWorkflow()
    client = TestClient(app)

    project = client.post(
        "/api/projects",
        json={"name": "并行审校进度", "default_user_brief": {"title": "测试"}, "default_target_chapters": 1},
    ).json()
    run = client.post(f"/api/projects/{project['project_id']}/runs", json={}).json()

    deadline = time.time() + 2
    run_snapshot = None
    while time.time() < deadline:
        candidate = client.get(f"/api/runs/{run['run_id']}").json()
        review_progress = candidate["result"]["progress"]["review_progress"]
        if review_progress["completed_count"] >= 2:
            run_snapshot = candidate
            break
        time.sleep(0.02)

    assert run_snapshot is not None
    review_progress = run_snapshot["result"]["progress"]["review_progress"]
    assert review_progress["stage_status"] == "running"
    assert review_progress["completed_count"] == 2
    assert set(review_progress["active_reviewers"]) == {"style", "reader_sim"}
    assert review_progress["pending_reviewers"] == []
    assert review_progress["reviewers"]["continuity"]["decision"] == "pass"
    assert review_progress["reviewers"]["pacing"]["decision"] == "rewrite"
    assert review_progress["reviewers"]["style"]["stalled_for_seconds"] >= 0

    release_run.set()
    wait_for_run(client, run["run_id"])


def test_mark_failed_prevents_late_background_overwrite() -> None:
    app = create_app(
        config=AppConfig(
            stub_mode=True,
            openai_api_key=None,
            admin_token=None,
            database_url="sqlite:///:memory:",
            model_name="gpt-5-nano",
            project_id="api-test",
            operator_id="tester",
        ),
        store=InMemoryStore(),
    )
    release_run = Event()

    class FakeWorkflow:
        def prepare_project_request(self, *, project, user_brief, target_chapters, operator_id, quick_mode=False):
            return {
                "user_brief": user_brief or project.default_user_brief,
                "target_chapters": target_chapters or project.default_target_chapters,
                "operator_id": operator_id or "tester",
                "quick_mode": quick_mode,
                "human_instruction": None,
            }

        def run_project(self, *, project, request_payload, on_update=None):
            state = {
                "creative_contract": {"working_title": "测试标题"},
                "current_card": {"chapter_no": 1, "purpose": "测试章卡"},
                "event_log": ["creative_contract_ready"],
                "rewrite_count": 0,
            }
            if on_update is not None:
                on_update("chapter_planner", state)
            release_run.wait(timeout=2)
            return {
                **state,
                "publish_package": {"chapter_no": 1, "title": "第1章", "full_text": "正文"},
            }

    app.state.workflow = FakeWorkflow()
    client = TestClient(app)

    project = client.post(
        "/api/projects",
        json={"name": "手动失败测试", "default_user_brief": {"title": "测试"}, "default_target_chapters": 1},
    ).json()
    run = client.post(f"/api/projects/{project['project_id']}/runs", json={}).json()

    deadline = time.time() + 2
    while time.time() < deadline:
        current = client.get(f"/api/runs/{run['run_id']}").json()
        if current["result"] and current["result"].get("progress", {}).get("latest_event"):
            break
        time.sleep(0.02)

    mark_failed = client.post(f"/api/runs/{run['run_id']}/mark-failed")
    assert mark_failed.status_code == 200
    assert mark_failed.json()["status"] == "failed"
    assert "人工标记失败" in mark_failed.json()["error"]

    release_run.set()
    time.sleep(0.1)

    still_failed = client.get(f"/api/runs/{run['run_id']}").json()
    assert still_failed["status"] == "failed"
    assert "manual_fail" == still_failed["result"]["progress"]["latest_event"]


def test_retry_failed_run_creates_new_background_run() -> None:
    app = create_app(
        config=AppConfig(
            stub_mode=True,
            openai_api_key=None,
            admin_token=None,
            database_url="sqlite:///:memory:",
            model_name="gpt-5-nano",
            project_id="api-test",
            operator_id="tester",
        ),
        store=InMemoryStore(),
    )

    class FakeWorkflow:
        def __init__(self) -> None:
            self.calls = 0

        def prepare_project_request(self, *, project, user_brief, target_chapters, operator_id, quick_mode=False):
            return {
                "user_brief": user_brief or project.default_user_brief,
                "target_chapters": target_chapters or project.default_target_chapters,
                "operator_id": operator_id or "tester",
                "quick_mode": quick_mode,
                "human_instruction": None,
            }

        def run_project(self, *, project, request_payload, on_update=None):
            self.calls += 1
            if self.calls == 1:
                raise ValueError("boom")
            return {
                "creative_contract": {"working_title": request_payload["user_brief"]["title"]},
                "current_card": {"chapter_no": 1, "purpose": "retry"},
                "publish_package": {"chapter_no": 1, "title": "第1章", "full_text": "正文"},
                "feedback_summary": {"chapter_no": 1},
                "event_log": ["retry_success"],
            }

    app.state.workflow = FakeWorkflow()
    client = TestClient(app)

    project = client.post(
        "/api/projects",
        json={"name": "重试测试", "default_user_brief": {"title": "重试标题"}, "default_target_chapters": 1},
    ).json()

    initial_run = client.post(
        f"/api/projects/{project['project_id']}/runs",
        json={"operator_id": "starter"},
    ).json()
    failed_run = wait_for_run(client, initial_run["run_id"])
    assert failed_run["status"] == "failed"

    retry_response = client.post(
        f"/api/runs/{initial_run['run_id']}/retry",
        headers={"x-operator-id": "retrier"},
    )
    assert retry_response.status_code == 201
    retry_run = retry_response.json()
    assert retry_run["run_id"] != initial_run["run_id"]
    assert retry_run["request"]["user_brief"]["title"] == "重试标题"
    assert retry_run["request"]["operator_id"] == "retrier"

    completed_retry = wait_for_run(client, retry_run["run_id"])
    assert completed_retry["status"] == "completed"


def test_stale_running_run_auto_transitions_to_failed() -> None:
    app = create_app(
        config=AppConfig(
            stub_mode=True,
            openai_api_key=None,
            admin_token=None,
            database_url="sqlite:///:memory:",
            model_name="gpt-5-nano",
            project_id="api-test",
            operator_id="tester",
        ),
        store=InMemoryStore(),
    )
    client = TestClient(app)

    project = client.post(
        "/api/projects",
        json={"name": "超时测试", "default_user_brief": {"title": "测试"}, "default_target_chapters": 1},
    ).json()
    stale_updated_at = (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat()
    run = app.state.store.save_run(
        project_id=project["project_id"],
        status="running",
        request={"user_brief": {"title": "测试"}, "target_chapters": 1, "operator_id": "tester"},
        result={
            "progress": {
                "current_node": "chapter_planner",
                "latest_event": "chapter_card_ready:1",
                "event_log_tail": ["chapter_card_ready:1"],
                "chapter_no": 1,
                "rewrite_count": 0,
                "phase_decision": "replan",
                "updated_at": stale_updated_at,
                "stage_goal": "重新规划第 1 章章卡。",
                "possible_cause": "等待上游返回",
                "review_progress": {
                    "stage_status": "running",
                    "stage_started_at": stale_updated_at,
                    "completed_count": 3,
                    "total_count": 4,
                    "active_reviewers": ["style"],
                    "pending_reviewers": [],
                    "longest_wait_reviewer": "style",
                    "longest_wait_seconds": 1200,
                    "stall_hint": "当前最可能卡在 文风审校。",
                    "reviewers": {
                        "style": {
                            "status": "running",
                            "started_at": stale_updated_at,
                            "finished_at": None,
                            "decision": None,
                            "total_score": None,
                            "stalled_for_seconds": 1200,
                        }
                    },
                },
            }
        },
        error=None,
    )

    response = client.get(f"/api/runs/{run.run_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "failed"
    assert "自动判定该运行已超时" in payload["error"]
    assert "文风审校" in payload["error"]
    assert payload["result"]["manual_intervention"]["action"] == "auto_timeout"
