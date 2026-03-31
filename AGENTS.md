# Repository Guidelines

## Project Structure & Module Organization
`novel_studio/` contains the Python application. Core API and workflow code lives in `novel_studio/novel_app/`, prompt templates are in `novel_studio/novel_app/prompts/`, utility scripts are in `novel_studio/scripts/`, and tests are in `novel_studio/tests/`. Deployment assets live at the repo root: `docker-compose.yml` for the VPS stack, `ops/` for backup and health scripts, `deploy/systemd/` for unit files, and `deploy/caddy/` for reverse-proxy examples. Use `docs/` for product and operations documentation, not implementation notes.

## Build, Test, and Development Commands
Run application commands from `novel_studio/`:

- `make install`: create `.venv` and install app, dev deps, and `langgraph-cli`.
- `make env-check`: validate required environment variables.
- `make db-init`: initialize the local database defined by `DATABASE_URL`.
- `make test`: run the `pytest` suite.
- `make smoke`: execute the stub workflow end to end.
- `make serve`: start the FastAPI app on `HOST`/`PORT`.

Run deployment commands from the repository root:

- `make up`: build and start the Compose stack from `.env.compose`.
- `make ps` / `make logs`: inspect running services.
- `make health-check`: run the VPS health script.

## Coding Style & Naming Conventions
Target Python 3.11+ with 4-space indentation and standard PEP 8 naming: `snake_case` for modules/functions, `PascalCase` for classes, and explicit, descriptive filenames such as `chapter_planner.py`. Keep prompt files and docs in clear, task-oriented names. `ruff` is included in dev dependencies; use it for linting before opening a PR when you touch Python code.

## Testing Guidelines
Tests use `pytest` and live under `novel_studio/tests/`. Name files `test_*.py` and keep new tests close to the feature being changed, for example `test_api.py` or `test_workflow.py`. Add or update tests for API behavior, workflow transitions, and persistence changes. Run `make test` for full coverage and `make smoke` for a quick integration check in stub mode.

## Commit & Pull Request Guidelines
Follow the existing commit style: Conventional Commit prefixes such as `feat:`, `fix:`, and `docs:` with a short imperative summary. Keep commits focused and reviewable. PRs should describe the user-visible change, note config or migration impact, link any issue or task, and include screenshots only when UI files such as `admin_static/` change.

## Security & Configuration Tips
Do not commit populated `.env`, `.env.compose`, API keys, or production tokens. Set `NOVEL_STUDIO_ADMIN_TOKEN` to a strong secret outside examples. Default to stub mode for local work unless model-backed behavior is being tested intentionally.
