# 20 OMX适配层MVP实施计划

## 1. 目标

在现有 NovelStudio 内部直接落一版可用的 `OMX Adapter MVP`，让上层更自由的 OMX 对话层可以先完成意图澄清，再把整理后的结果交给 NovelStudio 执行工作流。

这一版不另起独立服务，直接作为 NovelStudio FastAPI 的一组新接口提供：

- `POST /omx-adapter/v1/tasks`
- `GET /omx-adapter/v1/tasks/{task_id}`
- `POST /omx-adapter/v1/tasks/{task_id}/human-action`

## 2. 核心边界

### OMX 上层负责

- 用更自然的对话方式采集作者意图
- 输出项目简报、阶段目标、人工约束、补充说明
- 在 `awaiting_approval` 时承接人工决策

### NovelStudio 下层负责

- 将输入转为工作流 request payload
- 运行采访/设定/卷纲/写作/审校/发布流程
- 维护 run、approval、artifacts、canon

### Adapter 负责

- 将 OMX 输入映射为 NovelStudio 当前真实 API 所需结构
- 记录 `task_id -> project_id -> current_run_id` 关系
- 聚合 run 状态，返回 OMX 侧可读的任务状态
- 在人工动作时将批准意见和补充 instruction 注入 followup run

## 3. MVP范围

### 3.1 本期实现

1. OMX 任务持久化
2. 幂等任务创建
3. 项目创建与 run 发起
4. 任务状态轮询聚合
5. 自动识别 `awaiting_approval`
6. 人工动作回写并续跑
7. 输出 `publish_package / canon_state / phase_decision`

### 3.2 本期不做

- 外部回调推送
- 多租户隔离
- 完整审计报表
- 独立 Adapter 部署进程
- OMX 自带的角色/模板执行引擎

## 4. 数据模型

新增 `OmxTask` 持久化对象：

- `task_id`
- `project_id`
- `current_run_id`
- `latest_approval_id`
- `status`
- `operator_id`
- `idempotency_key`
- `source_payload`
- `latest_snapshot`
- `last_error`
- `created_at`
- `updated_at`
- `completed_at`

状态枚举：

- `running`
- `awaiting_approval`
- `completed`
- `failed`
- `rejected`

## 5. 输入映射

OMX 输入先映射为项目默认 brief：

- `project.working_title -> default_user_brief.title`
- `project.platform -> default_user_brief.platform`
- `project.genre -> default_user_brief.genre`
- `user_brief.one_sentence_hook -> default_user_brief.hook`
- `user_brief.must_have -> default_user_brief.must_have`
- `user_brief.must_not_have -> default_user_brief.must_not_have`
- `user_brief.tone -> default_user_brief.tone`

阶段性内容不写死进 brief，而作为本轮 run 的 `human_instruction`：

- `planning.phase_goal`
- `human_instruction.strict_rules`
- `human_instruction.notes`
- `human_instruction.must_fix`
- `human_instruction.risk_guard`

## 6. 接口设计

### 6.1 创建任务

`POST /omx-adapter/v1/tasks`

行为：

1. 校验 `Idempotency-Key`
2. 创建 project
3. 生成首个 run request payload
4. 存储 task
5. 启动后台 run

### 6.2 查询任务

`GET /omx-adapter/v1/tasks/{task_id}`

行为：

1. 读取 task
2. 读取 current run
3. 聚合 progress / approval / output
4. 回写 `latest_snapshot`

### 6.3 人工动作

`POST /omx-adapter/v1/tasks/{task_id}/human-action`

本期支持动作：

- `approve_continue`
- `approve_patch`
- `approve_replan`
- `provide_human_instruction`
- `reject`

说明：

- `approve_patch` 映射为 NovelStudio followup `rewrite`
- `approve_replan` 映射为 `replan`
- `approve_continue` 映射为 `continue`
- `provide_human_instruction` 在批准基础上，将 instruction 合并进 followup request 的 `human_instruction`

## 7. 实现步骤

1. 新增 OMX Task 的 dataclass / SQL model / store 方法
2. 新增 API schemas
3. 在 `api/app.py` 中实现 Adapter 专用 helper
4. 落地 3 个接口
5. 增加最小测试
6. 通过语法检查与本地 smoke

## 8. 验收标准

满足以下条件即视为 MVP 可用：

1. 能通过 OMX task API 创建项目并发起 run
2. 能查询到运行中、待人工、完成、失败状态
3. 遇到 `awaiting_approval` 时可通过 human-action 续跑
4. 完成后能返回最小输出摘要
5. 不破坏现有 NovelStudio 前台与原 API

## 9. 后续演进

MVP 稳定后，再继续：

1. 把 `oh-my-codex-webnovel` 的模板产物接入 OMX 输入规范
2. 增加 callback 模式
3. 支持 task 绑定已有 project，形成“自由访谈 -> 多轮执行”长链路
4. 将 Adapter 独立成单独服务
