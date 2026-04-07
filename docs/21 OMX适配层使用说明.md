# 21 OMX适配层使用说明

## 1. 当前形态

这一版 `OMX Adapter MVP` 已经接入 NovelStudio 后端。它仍保留管理 API 入口，但作者侧也已经补上了第一版线程内桥接。

适合的使用方式是：

1. 上层 OMX 或其它自由对话层先完成意图澄清
2. 再把整理后的结构化结果提交到 NovelStudio
3. 通过轮询任务状态，决定继续等待还是进行人工干预

生产入口：

- `https://novel.jiamusoft.eu.cc/omx-adapter/v1/tasks`

所有接口都需要管理员令牌：

- Header: `x-api-key: <NOVEL_STUDIO_ADMIN_TOKEN>`

### 1.1 已接入的站内入口

现在前台已经补上第一版内部桥接：

- 立项共创线程中，可直接点击“按这版项目方向进入执行”
- 人物讨论线程中，可直接点击“按这版人物结果进入执行”
- 卷纲讨论线程中，也可直接按当前阶段结果发起 OMX
- 系统会先把当前阶段摘要自动写回项目，再发起 OMX 任务
- 发起后，线程页会显示该线程最近一次 OMX 任务状态
- 如果任务进入 `awaiting_approval`，线程页可直接继续批准、退回或补充人工说明

这条站内入口走的是内部 `/api/...` 接口，普通已登录作者也能用，不需要自己手工拼外部 OMX 请求。

当前内部接口包括：

- `POST /api/conversation-threads/{thread_id}/launch-omx-task`
- `GET /api/conversation-threads/{thread_id}/omx-task`
- `POST /api/conversation-threads/{thread_id}/omx-task/human-action`

## 2. 基本调用流程

### 2.1 创建任务

`POST /omx-adapter/v1/tasks`

建议同时传 `Idempotency-Key`，避免上层重试时重复创建任务。

```bash
curl https://novel.jiamusoft.eu.cc/omx-adapter/v1/tasks \
  -H 'x-api-key: <ADMIN_TOKEN>' \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: omx-demo-001' \
  -d '{
    "operator_id": "omx-editor",
    "project": {
      "working_title": "九霄夜行",
      "platform": "番茄",
      "genre": "都市修仙"
    },
    "planning": {
      "target_chapters": 1,
      "phase_goal": "先完成首章试写"
    },
    "user_brief": {
      "one_sentence_hook": "失去灵根的少年在城市底层逆袭。",
      "must_have": ["成长爽点", "章末钩子"],
      "must_not_have": ["大段设定灌输"],
      "tone": "克制但有爆点"
    },
    "human_instruction": {
      "strict_rules": ["第一章不引入超过3个新名词"],
      "notes": "优先保证可读性"
    }
  }'
```

返回结果里最重要的是：

- `task_id`
- `project_id`
- `run_id`
- `poll_url`

### 2.2 查询任务状态

`GET /omx-adapter/v1/tasks/{task_id}`

```bash
curl https://novel.jiamusoft.eu.cc/omx-adapter/v1/tasks/<TASK_ID> \
  -H 'x-api-key: <ADMIN_TOKEN>'
```

常见状态：

- `running`: 正在执行
- `awaiting_approval`: 等待人工动作
- `completed`: 已完成，可读取 `output`
- `failed`: 执行失败
- `rejected`: 人工拒绝

## 3. 人工动作

当状态变成 `awaiting_approval` 时，调用：

- `POST /omx-adapter/v1/tasks/{task_id}/human-action`

可用动作：

- `approve_continue`
- `approve_patch`
- `approve_replan`
- `provide_human_instruction`
- `reject`

示例：补充人工要求并续跑。

```bash
curl https://novel.jiamusoft.eu.cc/omx-adapter/v1/tasks/<TASK_ID>/human-action \
  -H 'x-api-key: <ADMIN_TOKEN>' \
  -H 'Content-Type: application/json' \
  -d '{
    "action": "provide_human_instruction",
    "instruction": {
      "must_fix": ["统一世界术语“灵汐”定义"],
      "notes": "先统一术语，再继续当前章节",
      "risk_guard": ["不要引入新组织"]
    },
    "comment": "优先修术语，不要扩写新设定。"
  }'
```

## 4. 当前限制

- 虽然作者已可在线程内发起和处理任务，但底层管理接口本身仍不对普通前台用户直接开放
- 当前是轮询模式，没有 callback 推送
- 当前更适合作为“自由 OMX 对话层 -> NovelStudio 工作流”的桥接层
- 线程页现在能承接最小闭环，但还不是完整的 OMX 专用操作台
