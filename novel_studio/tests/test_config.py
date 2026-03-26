import pytest

from novel_app.config import AppConfig, load_config, validate_config


def test_validate_config_requires_openai_key_in_llm_mode() -> None:
    config = AppConfig(
        stub_mode=False,
        openai_api_key=None,
        openai_base_url=None,
        admin_token=None,
        database_url="sqlite:///./novel_studio.db",
        model_name="gpt-5-nano",
        project_id="demo-book",
        operator_id="local-dev",
    )
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        validate_config(config)


def test_load_config_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NOVEL_STUDIO_STUB_MODE", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://relay.example.com/v1")
    monkeypatch.setenv("NOVEL_STUDIO_ADMIN_TOKEN", "secret")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")
    monkeypatch.setenv("NOVEL_STUDIO_MODEL", "gpt-5-mini")
    monkeypatch.setenv("NOVEL_STUDIO_PROJECT_ID", "project-1")
    monkeypatch.setenv("NOVEL_STUDIO_OPERATOR_ID", "operator-1")

    config = load_config()

    assert config.stub_mode is False
    assert config.openai_api_key == "test-key"
    assert config.openai_base_url == "https://relay.example.com/v1"
    assert config.admin_token == "secret"
    assert config.database_url == "sqlite:///./test.db"
    assert config.model_name == "gpt-5-mini"
    assert config.project_id == "project-1"
    assert config.operator_id == "operator-1"


def test_load_config_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in [
        "NOVEL_STUDIO_STUB_MODE",
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "NOVEL_STUDIO_OPENAI_BASE_URL",
        "NOVEL_STUDIO_ADMIN_TOKEN",
        "DATABASE_URL",
        "NOVEL_STUDIO_MODEL",
        "NOVEL_STUDIO_PROJECT_ID",
        "NOVEL_STUDIO_OPERATOR_ID",
    ]:
        monkeypatch.delenv(key, raising=False)

    config = load_config()

    assert config.stub_mode is True
    assert config.openai_api_key is None
    assert config.openai_base_url is None
    assert config.admin_token is None
    assert config.database_url == "sqlite:///./novel_studio.db"
    assert config.model_name == "gpt-5-nano"
    assert config.project_id == "demo-book"
    assert config.operator_id == "local-dev"


def test_validate_config_rejects_blank_openai_base_url() -> None:
    config = AppConfig(
        stub_mode=False,
        openai_api_key="test-key",
        openai_base_url="   ",
        admin_token=None,
        database_url="sqlite:///./novel_studio.db",
        model_name="gpt-5-nano",
        project_id="demo-book",
        operator_id="local-dev",
    )
    with pytest.raises(ValueError, match="OPENAI_BASE_URL"):
        validate_config(config)
