from __future__ import annotations

import os
from dataclasses import dataclass

from novel_app.state import RuntimeContext


TRUE_VALUES = {"1", "true", "yes", "on"}


def parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in TRUE_VALUES


@dataclass(frozen=True)
class AppConfig:
    stub_mode: bool
    openai_api_key: str | None
    admin_token: str | None
    database_url: str
    model_name: str
    project_id: str
    operator_id: str
    openai_base_url: str | None = None
    writer_registration_limit: int = 5

    def to_runtime_context(self) -> RuntimeContext:
        return RuntimeContext(
            project_id=self.project_id,
            operator_id=self.operator_id,
            model_name=self.model_name,
            openai_base_url=self.openai_base_url,
        )


def load_config() -> AppConfig:
    config = AppConfig(
        stub_mode=parse_bool(os.getenv("NOVEL_STUDIO_STUB_MODE"), True),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_base_url=os.getenv("OPENAI_BASE_URL") or os.getenv("NOVEL_STUDIO_OPENAI_BASE_URL"),
        admin_token=os.getenv("NOVEL_STUDIO_ADMIN_TOKEN"),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./novel_studio.db"),
        model_name=os.getenv("NOVEL_STUDIO_MODEL", "gpt-5-nano"),
        project_id=os.getenv("NOVEL_STUDIO_PROJECT_ID", "demo-book"),
        operator_id=os.getenv("NOVEL_STUDIO_OPERATOR_ID", "local-dev"),
        writer_registration_limit=max(1, int(os.getenv("NOVEL_STUDIO_WRITER_REGISTRATION_LIMIT", "5"))),
    )
    validate_config(config)
    return config


def validate_config(config: AppConfig) -> None:
    if not config.stub_mode and not config.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required when NOVEL_STUDIO_STUB_MODE=false")

    if not config.project_id.strip():
        raise ValueError("NOVEL_STUDIO_PROJECT_ID must not be empty")

    if not config.operator_id.strip():
        raise ValueError("NOVEL_STUDIO_OPERATOR_ID must not be empty")

    if not config.model_name.strip():
        raise ValueError("NOVEL_STUDIO_MODEL must not be empty")

    if not config.database_url.strip():
        raise ValueError("DATABASE_URL must not be empty")

    if config.openai_base_url is not None and not config.openai_base_url.strip():
        raise ValueError("OPENAI_BASE_URL must not be empty when set")
