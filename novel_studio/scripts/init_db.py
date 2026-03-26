from __future__ import annotations

from novel_app.config import load_config
from novel_app.services.sql_store import SqlAlchemyStore


def main() -> None:
    config = load_config()
    store = SqlAlchemyStore(config.database_url)
    store.create_tables()
    print(f"db_initialized database_url={config.database_url}")


if __name__ == "__main__":
    main()
