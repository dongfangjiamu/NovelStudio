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
    return TestClient(app)


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
        headers={"x-operator-id": "editor-a"},
        json={"name": "测试项目", "default_user_brief": {"title": "长夜炉火"}},
    ).json()

    audit_logs = client.get("/api/audit-logs").json()

    assert len(audit_logs) >= 1
    assert audit_logs[0]["action"] == "project.create"
    assert audit_logs[0]["actor"] == "editor-a"
    assert audit_logs[0]["project_id"] == project["project_id"]
