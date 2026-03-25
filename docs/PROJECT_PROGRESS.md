# Project Progress & Review Summary | 项目进度与审阅汇总

## 1. 审阅报告摘要 (Review Summary)

本项目已成功将“最初构思”中的宏大设计（13角色+7阶段）务实地收缩为基于 **LangGraph** 的最小可运行骨架。

### ✅ 核心达成
- **角色分工**：落地了 12 个图节点，覆盖了 8 个核心角色与关键流程门禁。
- **工件驱动**：建立了以 `NovelState` 为核心的状态机，通过结构化 Schema 约束 Prompt 输出。
- **质量分层**：实现了“硬违规（Replan）/ 主要问题（Rewrite）/ 次要问题（Defer）”三级裁决逻辑。
- **架构解耦**：支持 Stub 模式与 LLM 模式切换，方便本地调试。

### 🟡 待完善点
- 自动校验门禁（Gate A-D）尚未完全代码化。
- 缺乏跨章节的叙事回归测试（Regression Test）。
- 审校节点目前仅为确定性逻辑占位。

---

## 2. 目前已执行步骤 (Completed Steps)

### 🚀 基础设施建设
- **GitHub 托管**：创建了仓库 [dongfangjiamu/NovelStudio](https://github.com/dongfangjiamu/NovelStudio)，完成了代码首推。
- **环境隔离**：配置了 `.gitignore` 和 `pyproject.toml`，支持 `pip install -e .`。

### 🛠️ P0 级问题修复
- **[P0-1] 重写循环上限**：在 `NovelState` 中引入 `rewrite_count`，设置 `MAX_REWRITES = 3` 阈值。超过次数自动转入 `human_gate`（人工干预），防止 LLM 无限重写。
- **[P0-2] 章节循环闭环**：
    - 修改 `graph_main.py`，将单次运行改为基于 `target_chapters` 的条件循环。
    - `feedback_ingest` 节点现在负责递增章节计数并重置单章运行态（重写次数、审校报告）。
    - 更新 `smoke_run.py` 以支持多章自动化测试。

---

## 3. 后续建议执行步骤 (Next Steps)

### 🔴 优先级：P0 (实测前置)
- **[P0-3] 真实环境验证**：在安装了 `langgraph` 的 Python 3.11+ 环境中运行 `pytest` 和 `smoke_run.py`，确认 API 兼容性。

### 🟠 优先级：P1 (实测增强)
- **真·交互网关**：利用 LangGraph 的 `interrupt` 能力实现真正的 `human-in-the-loop`，允许作者在节点间进行干预。
- **结构化校验**：为 `contract_gate`、`bible_gate` 等添加基于 Pydantic 的自动内容校验。

### 🔵 优先级：P2 (长期演进)
- **叙事回归测试**：引入跨章扫描器，检查伏笔是否回收、人设是否偏移。
- **LLM 审校接入**：将 4 个 Reviewer 节点从 Stub 替换为真实的 LLM 调用。
- **长效记忆存储**：将 `creative_contract` 等长期工件移入 LangGraph Store，实现跨 Thread 的知识复用。
