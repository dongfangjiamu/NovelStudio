from __future__ import annotations

from novel_app.config import load_config


def main() -> None:
    config = load_config()
    mode = "stub" if config.stub_mode else "llm"
    auth_mode = "token" if config.admin_token else "open"
    print(
        "config_ok "
        f"mode={mode} model={config.model_name} project_id={config.project_id} "
        f"database_url={config.database_url} auth={auth_mode}"
    )


if __name__ == "__main__":
    main()
