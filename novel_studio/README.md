# Novel Studio

一个面向中文网文长篇连载的 LangGraph 仓库骨架。它把“采访官 → 设定师 → 卷纲师 → 章节策划 → 执笔者 → 审校团 → 总编 → 发布/Canon 回写”串成一个可运行的工作流。

当前版本刻意做成 **最小可运行骨架**：

- 默认支持 `NOVEL_STUDIO_STUB_MODE=true`，不开模型也能跑通流程
- 切换到真实模型后，采访官 / 设定师 / 卷纲师 / 章节策划 / 执笔者这些节点可直接走结构化输出
- 审校、总编裁决、发布包、Canon 回写先用确定性逻辑实现，方便先把系统跑起来

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
```

先用 stub 模式跑通：

```bash
python scripts/smoke_run.py
```

或者启动本地 Agent Server：

```bash
pip install -U "langgraph-cli[inmem]"
langgraph dev
```

预发验证建议用：

```bash
langgraph up --watch
```

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

- 我在当前环境里无法安装 `langgraph` 依赖，所以这里做了**语法级检查**与单元测试（router/schema/裁决逻辑），没有做真实的 LangGraph 运行验证。
- 只要你在本地按 `pip install -e ".[dev]"` 安装依赖，就可以立刻进入联调。
