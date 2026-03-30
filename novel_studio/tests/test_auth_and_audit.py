from fastapi.testclient import TestClient

from novel_app.api.app import create_app
from novel_app.config import AppConfig
from novel_app.services.store import InMemoryStore


def make_client(admin_token: str | None) -> TestClient:
    app = create_app(
        config=AppConfig(
            stub_mode=True,
            openai_api_key=None,
            admin_token=admin_token,
            database_url="sqlite:///:memory:",
            model_name="gpt-5-nano",
            project_id="auth-test",
            operator_id="tester",
        ),
        store=InMemoryStore(),
    )
    client = TestClient(app)
    if admin_token is None:
        response = client.post("/api/auth/register", json={"pen_name": "writer-a", "password": "password123"})
        assert response.status_code == 201, response.text
    return client


def test_api_requires_token_when_configured() -> None:
    client = make_client("secret-token")

    unauthorized = client.post("/api/projects", json={"name": "x"})
    authorized = client.post(
        "/api/projects",
        headers={"x-api-key": "secret-token"},
        json={"name": "x"},
    )

    assert unauthorized.status_code == 401
    assert authorized.status_code == 201


def test_audit_logs_are_recorded_for_write_operations() -> None:
    client = make_client(None)

    project = client.post(
        "/api/projects",
        json={"name": "测试项目", "default_user_brief": {"title": "长夜炉火"}},
    ).json()

    audit_logs = client.get("/api/audit-logs").json()

    assert len(audit_logs) >= 1
    assert audit_logs[0]["action"] == "project.create"
    assert audit_logs[0]["actor"] == "writer-a"
    assert audit_logs[0]["project_id"] == project["project_id"]


def test_registration_limit_is_enforced() -> None:
    app = create_app(
        config=AppConfig(
            stub_mode=True,
            openai_api_key=None,
            admin_token=None,
            database_url="sqlite:///:memory:",
            model_name="gpt-5-nano",
            project_id="auth-test",
            operator_id="tester",
            writer_registration_limit=2,
        ),
        store=InMemoryStore(),
    )
    client = TestClient(app)

    assert client.post("/api/auth/register", json={"pen_name": "writer-1", "password": "password123"}).status_code == 201
    logout_1 = client.post("/api/auth/logout")
    assert logout_1.status_code == 204
    assert client.post("/api/auth/register", json={"pen_name": "writer-2", "password": "password123"}).status_code == 201
    logout_2 = client.post("/api/auth/logout")
    assert logout_2.status_code == 204
    blocked = client.post("/api/auth/register", json={"pen_name": "writer-3", "password": "password123"})

    assert blocked.status_code == 403
    assert blocked.json()["detail"] == "registration_limit_reached"


def test_single_character_pen_name_is_allowed() -> None:
    app = create_app(
        config=AppConfig(
            stub_mode=True,
            openai_api_key=None,
            admin_token=None,
            database_url="sqlite:///:memory:",
            model_name="gpt-5-nano",
            project_id="auth-test",
            operator_id="tester",
        ),
        store=InMemoryStore(),
    )
    client = TestClient(app)

    registered = client.post("/api/auth/register", json={"pen_name": "玲", "password": "password123"})
    assert registered.status_code == 201, registered.text
    assert registered.json()["pen_name"] == "玲"

    assert client.post("/api/auth/logout").status_code == 204

    logged_in = client.post("/api/auth/login", json={"pen_name": "玲", "password": "password123"})
    assert logged_in.status_code == 200, logged_in.text
    assert logged_in.json()["pen_name"] == "玲"


def test_writer_can_only_see_own_projects() -> None:
    app = create_app(
        config=AppConfig(
            stub_mode=True,
            openai_api_key=None,
            admin_token=None,
            database_url="sqlite:///:memory:",
            model_name="gpt-5-nano",
            project_id="auth-test",
            operator_id="tester",
        ),
        store=InMemoryStore(),
    )
    client_a = TestClient(app)
    assert client_a.post("/api/auth/register", json={"pen_name": "writer-a", "password": "password123"}).status_code == 201
    project_a = client_a.post("/api/projects", json={"name": "A项目", "default_user_brief": {"title": "A书"}}).json()

    client_b = TestClient(app)
    assert client_b.post("/api/auth/register", json={"pen_name": "writer-b", "password": "password123"}).status_code == 201
    projects_b = client_b.get("/api/projects")
    project_a_from_b = client_b.get(f"/api/projects/{project_a['project_id']}")

    assert projects_b.status_code == 200
    assert projects_b.json() == []
    assert project_a_from_b.status_code == 404
