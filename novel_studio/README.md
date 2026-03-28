# Novel Studio

一个面向中文网文长篇连载的 LangGraph 仓库骨架。它把“采访官 → 设定师 → 卷纲师 → 章节策划 → 执笔者 → 审校团 → 总编 → 发布/Canon 回写”串成一个可运行的工作流。

当前版本刻意做成 **最小可运行骨架**：

- 默认支持 `NOVEL_STUDIO_STUB_MODE=true`，不开模型也能跑通流程
- 切换到真实模型后，采访官 / 设定师 / 卷纲师 / 章节策划 / 执笔者这些节点可直接走结构化输出
- 审校、总编裁决、发布包、Canon 回写先用确定性逻辑实现，方便先把系统跑起来
- 当前已补最小 FastAPI 服务骨架，便于进入 API 联调

## 目录

```text
novel_studio/
├── novel_app/
│   ├── state.py
│   ├── schemas.py
│   ├── routers.py
│   ├── graph_main.py
│   ├── nodes/
│   ├── prompts/
│   └── utils/
├── scripts/
│   └── smoke_run.py
├── tests/
├── langgraph.json
├── pyproject.toml
└── .env.example
```

## 快速开始

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pip install -U "langgraph-cli[inmem]"
```

先检查配置：

```bash
python scripts/check_env.py
```

初始化本地数据库：

```bash
make db-init
```

如果你要启用最小管理员鉴权，在 `.env` 里设置：

```bash
NOVEL_STUDIO_ADMIN_TOKEN=改成高强度随机字符串
```

然后请求 API 时带上：

- `Authorization: Bearer <token>` 或
- `X-API-Key: <token>`

启动最小 API 服务：

```bash
make serve
```

如果 `8000` 端口被占用：

```bash
PORT=8010 make serve
```

`/healthz` 现在会同时返回数据库就绪状态，便于反向代理或容器健康检查使用。

然后访问：

- `GET /admin`
- `GET /healthz`
- `POST /api/projects`
- `GET /api/projects`
- `GET /api/projects/{project_id}/runs`
- `POST /api/projects/{project_id}/runs`
- `GET /api/runs/{run_id}`
- `GET /api/projects/{project_id}/chapters`
- `GET /api/projects/{project_id}/approval-requests`
- `GET /api/runs/{run_id}/artifacts`
- `POST /api/runs/{run_id}/approval-requests`
- `GET /api/approval-requests/{approval_id}`
- `POST /api/approval-requests/{approval_id}/resolve`
- `POST /api/approval-requests/{approval_id}/execute`
- `GET /api/audit-logs`

`POST /api/projects/{project_id}/runs` 和 `POST /api/approval-requests/{approval_id}/execute` 现在都会先返回一个 `status=running` 的 Run，实际工作流在后台线程中继续执行。前端或调用方应轮询 `GET /api/runs/{run_id}`，直到状态变成：

- `completed`
- `awaiting_approval`
- `failed`

审批流当前支持的最小闭环：

1. 生成 run
2. 创建审批申请
3. 审批通过
4. 执行审批动作
5. 基于已持久化工件续写下一章或重跑当前章

最小管理页当前支持：

- 查看项目列表
- 创建项目
- 查看章节、Runs、审批单
- 发起 Run
- 通过/驳回审批
- 执行审批动作
- 查看 Run 工件和审计日志

先用 stub 模式跑通：

```bash
python scripts/smoke_run.py
```

或者启动本地 Agent Server：

```bash
langgraph dev
```

预发验证建议用：

```bash
langgraph up --watch
```

## Docker Compose 单机部署

根目录已经提供 `docker-compose.yml`，适合在这台 VPS 上跑内部 Alpha 环境。

先准备 Compose 环境文件：

```bash
cp .env.compose.example .env.compose
```

默认是 `stub` 模式。若要切到真实模型，把 `.env.compose` 里的：

```bash
NOVEL_STUDIO_STUB_MODE=false
OPENAI_API_KEY=你的key
OPENAI_BASE_URL=
NOVEL_STUDIO_ADMIN_TOKEN=改成高强度随机字符串
```

如果你用的是 OpenAI 兼容中转服务，把 `OPENAI_BASE_URL` 改成对方提供的接口根地址，例如 `https://your-relay.example.com/v1`。
当前也支持仅提供 `Responses API` 兼容入口的中转；系统会走结构化流式请求。

然后启动：

```bash
docker compose --env-file .env.compose up -d --build
```

查看状态：

```bash
docker compose ps
docker compose logs -f app
curl http://127.0.0.1:${APP_PORT:-18080}/healthz
```

当前 Compose 特性：

- `postgres` 和 `redis` 都带健康检查
- `app` 会等待依赖服务健康后再启动
- `app` 健康检查会校验 `/healthz` 与数据库连通性
- `app` 默认只绑定到 `127.0.0.1`，避免直接暴露到公网
- 宿主机端口通过 `APP_PORT` 配置，默认 `18080`，避免与 VPS 上其他服务冲突
- 适合作为单机内部系统部署骨架

根目录还提供了常用运维命令：

```bash
cp .env.compose.example .env.compose
make up
make ps
make logs
make backup-db
make prune-backups
make backup-cycle
make print-backup-cron
make health-check
make systemd-verify
make restore-db BACKUP=/abs/path/to/backup.sql.gz
```

备份恢复说明见：

- `docs/06 单机备份与恢复手册.md`
- `docs/07 单机反代与定时任务说明.md`
- `docs/08 单机自恢复与巡检说明.md`
- `docs/14 创作者使用说明.md`

## 运行模式

### 1) Stub 模式（默认）

`NOVEL_STUDIO_STUB_MODE=true`

- 不需要模型 API Key
- 用于调通图结构、状态流转、重写回路、Canon 回写
- 第一次运行会经历一轮 `rewrite -> patch -> pass`，方便你观察完整闭环

### 2) LLM 模式

修改 `.env`：

```bash
NOVEL_STUDIO_STUB_MODE=false
OPENAI_API_KEY=你的key
OPENAI_BASE_URL=
DATABASE_URL=sqlite:///./novel_studio.db
NOVEL_STUDIO_MODEL=gpt-5-nano
```

然后再次运行 `python scripts/smoke_run.py` 或 `langgraph dev`。

## 当前图结构

```text
START
  -> interviewer_contract
  -> lore_builder
  -> arc_planner
  -> chapter_planner
  -> draft_writer
  -> [continuity_reviewer, pacing_reviewer, style_reviewer, reader_simulator]
  -> chief_editor
     |- pass      -> release_prepare -> canon_commit -> feedback_ingest -> END
     |- rewrite   -> patch_writer    -> reviewers ...
     |- replan    -> chapter_planner
     |- human_check -> human_gate -> END
```

## 接下来建议你做的三件事

1. 把 `prompts/*.md` 从通用模板改成你的题材专用模板（男频玄幻 / 女频现言 / 悬疑等）。
2. 把 `schemas.py` 里的通用字段细化成你真正要持久化的 Story Bible / Canon 字段。
3. 把 `canon_commit` 从“轻量回写”升级成真正的 Canon 数据库同步逻辑。

## 重要说明

这是一个“仓库骨架”，不是已经调优完毕的生产系统：

- 当前仓库已验证可在 Python 3.11+ 环境安装依赖，并通过单元测试与 stub 集成测试。
- 当前已具备最小 API、SQLite 持久化、章节/工件落库与人工审批接口。
- 当前已具备可选管理员令牌鉴权、审计日志接口，以及 `docker-compose.yml` 单机部署骨架。
- 当前 `/healthz` 已包含数据库状态，可直接用于容器或反向代理探活。
- 当前审批流已能基于已持久化工件续写下一章，但还不是基于 LangGraph checkpoint 的真中断恢复。
- 当前已具备最小浏览器控制台 `/admin`，适合内部联调与人工操作。
- 生产化能力仍未完成，尤其是 Redis 实际接入、真实审校、正式角色权限、运维与监控层。
