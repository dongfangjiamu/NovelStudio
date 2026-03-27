import time
from datetime import datetime, timedelta, timezone
from threading import Event

from fastapi.testclient import TestClient

from novel_app.api.app import create_app
from novel_app.config import AppConfig
from novel_app.services.store import InMemoryStore


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
