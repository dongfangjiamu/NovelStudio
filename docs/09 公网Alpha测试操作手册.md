# 09 公网 Alpha 测试操作手册

## 1. 目的

本文档用于指导测试人员在当前公网 Alpha 环境中完成一轮标准化实测，覆盖以下能力：

- 公网访问与鉴权
- 项目创建
- 单章生成
- 运行进度观察
- 工件核对
- 审批与续写
- 审计日志核对
- 异常取证

本文档面向内部测试，不包含任何生产密钥。测试所需账号口令与 API Token 需由部署方单独发放。

## 2. 测试范围

本轮测试以“单项目、低并发、人工参与”的 Alpha 验证为目标，重点确认：

- 系统能否在公网入口正常访问
- 后台页能否完成从建项目到生成章节的最小闭环
- 真实模型模式下，Run 是否会进入后台执行并持续刷新状态
- 工件、审批、审计日志是否可查看且字段完整
- 审批后续写下一章是否可跑通

本轮测试不作为以下结论依据：

- 多项目高并发稳定性
- 长篇连载十章以上的一致性结论
- 最终内容质量定稿
- 对外开放运营可用性

## 3. 当前测试入口

如果本轮部署未变更，当前公网入口如下：

- 后台地址：`https://novel.jiamusoft.eu.cc/admin`

测试前请从部署方获取：

- Basic Auth 用户名
- Basic Auth 密码
- 后台 API Token
- 建议填写的 `Operator` 标识，例如 `editor-1`

## 4. 测试前准备

开始前请确认以下事项：

1. 使用桌面浏览器，优先 Chrome 或 Edge 最新版。
2. 本地网络能够稳定访问目标域名。
3. 已拿到本轮测试所需的 Basic Auth 和 API Token。
4. 测试期间不要同时开启大量并发 Run，建议同一时间只操作一个项目。
5. 如需记录问题，请准备截图工具，并记录精确时间。

## 5. 标准测试流程

### 5.1 公网入口与登录验证

操作步骤：

1. 打开 `https://novel.jiamusoft.eu.cc/admin`。
2. 浏览器弹出认证框时，输入 Basic Auth 用户名和密码。
3. 页面打开后，在左侧 `连接` 面板中填写：
   - `API Token`
   - `Operator`
4. 点击 `保存配置`。

验证事项：

- 页面能正常加载，不出现 502、504、证书告警或空白页。
- 页面标题为 `NovelStudio Admin`。
- 点击 `保存配置` 后右上状态区显示“连接配置已保存”或等价成功提示。

异常判定：

- 若浏览器持续弹出认证框，说明 Basic Auth 凭据错误。
- 若页面加载后频繁出现 `unauthorized`，说明 API Token 未填写或错误。
- 若静态资源加载失败，通常会表现为页面样式缺失或按钮无响应。

### 5.2 健康检查验证

浏览器方式：

1. 新标签页打开 `https://novel.jiamusoft.eu.cc/healthz`。
2. 通过 Basic Auth 后查看返回 JSON。

预期结果：

- `status` 为 `ok`
- `auth_mode` 为 `token`
- `database.status` 为 `ready`
- `stub_mode` 应与本轮测试模式一致

可选命令行验证：

```bash
curl -u "<basic_user>:<basic_password>" \
  https://novel.jiamusoft.eu.cc/healthz
```

### 5.3 创建测试项目

操作步骤：

1. 回到后台首页。
2. 在 `新建项目` 区域填写：
   - `项目名`：建议使用带日期的唯一名称，例如 `Alpha-Test-20260326-A`
   - `简介`：例如“公网 Alpha 首轮流程验证”
   - `默认章节数`：先填 `1`
   - `默认 Brief JSON`：保留默认值或使用下方推荐样例
3. 点击 `创建项目`。

推荐 Brief JSON：

```json
{
  "title": "长夜炉火",
  "genre": "东方玄幻",
  "platform": "起点中文网",
  "hook": "一个被逐出山门的外门弟子，靠偷听禁地炉火中的古老对话逆天改命。",
  "must_have": ["稳步升级", "师门阴谋", "章末钩子强"],
  "must_not_have": ["后宫泛滥", "无代价外挂"]
}
```

验证事项：

- 创建成功后，左侧 `项目` 列表出现新项目。
- 选中项目后，主区域标题切换为该项目名。
- `项目` 列表中可以看到对应 `project_id`。
- 右上状态区显示“项目已创建”或同类成功提示。

### 5.4 触发首个 Run

操作步骤：

1. 在已选中项目的前提下，点击 `生成章节`。
2. 观察右上状态区从“Run 已提交，正在后台执行…”切换到执行中状态。
3. 等待页面自动轮询，不要刷新页面。

验证事项：

- 点击后应快速返回，不应卡住浏览器数十秒。
- 状态区应显示 `Run 执行中: ...`。
- 初始阶段通常应看到类似：
  - `run_started`
  - `interviewer_contract`
- 随执行推进，状态会变化为其他节点或事件。

判定要点：

- 若点击按钮后长时间完全无反馈，属于异常。
- 若页面出现 `run_timeout`，说明本轮运行超出后台页等待时间，需要保留证据并由运维侧检查日志。
- 若状态最终变为 `failed`，需记录错误文案、时间和项目名。

### 5.5 查看章节与 Run 结果

操作步骤：

1. Run 完成后，查看中间区域的 `章节` 列。
2. 查看 `Runs` 列中最新一条记录。
3. 点击该 Run 的 `查看工件`。

验证事项：

- `章节` 列应出现至少一章。
- 最新 Run 状态应为以下之一：
  - `completed`
  - `awaiting_approval`
- `查看工件` 后，右侧 `Run 工件` 区应出现若干工件卡片。

最少应检查的工件：

- `creative_contract`
- `story_bible`
- `arc_plan`
- `current_card`
- `current_draft`
- `publish_package`
- `canon_state`
- `latest_review_reports`
- `event_log`

字段核对建议：

- `publish_package.chapter_no` 是否为 `1`
- `publish_package.title` 是否非空
- `publish_package.full_text` 是否存在正文
- `current_card.chapter_goal` 是否存在
- `latest_review_reports` 是否为结构化数组
- `canon_state` 是否含故事状态信息

### 5.6 审批与续写验证

本系统有两种情况：

- 情况 A：Run 自动进入 `awaiting_approval`
- 情况 B：Run 直接 `completed`

#### 情况 A：页面内直接审批

操作步骤：

1. 在 `审批` 列找到状态为 `pending` 的审批单。
2. 点击 `通过`。
3. 审批单状态变为 `approved` 后，点击 `执行`。
4. 等待系统后台续写。

验证事项：

- 点击 `通过` 后，审批单状态应变成 `approved`。
- 点击 `执行` 后，状态区应显示“续写任务已提交，正在后台执行…”。
- 待执行完成后，`章节` 列应出现下一章。
- 新生成章节的 `chapter_no` 应为 `2`。

#### 情况 B：通过 API 人工创建审批单后再执行

如果本次 Run 没有自动进入 `awaiting_approval`，可用以下接口补做审批链路验证。

1. 先在 `Runs` 列记下最新 `run_id`。
2. 使用下列命令创建审批单：

```bash
curl -u "<basic_user>:<basic_password>" \
  -H "x-api-key: <api_token>" \
  -H "x-operator-id: editor-1" \
  -H "content-type: application/json" \
  -X POST \
  "https://novel.jiamusoft.eu.cc/api/runs/<run_id>/approval-requests" \
  -d '{
    "requested_action": "continue",
    "reason": "手工触发续写链路验证",
    "chapter_no": 1,
    "payload": {
      "source": "manual-alpha-test"
    }
  }'
```

3. 回到后台页面，点击 `刷新` 或重新选中项目。
4. 在 `审批` 列中找到新审批单并点击 `通过`。
5. 点击 `执行`，等待完成。

验证事项：

- 审批单成功出现在页面中。
- 执行后出现新的 Run。
- 新 Run 完成后，第二章成功落库并可在工件中查看。

### 5.7 审计日志验证

操作步骤：

1. 点击页面右下区域的 `刷新`。
2. 查看最近 20 条审计日志。

验证事项：

本轮测试至少应看到以下动作中的大部分：

- `project.create`
- `run.create`
- `approval.create`
- `approval.resolve`
- `approval.execute`

每条日志至少检查：

- `actor` 是否为当前 Operator
- `created_at` 是否为本轮测试时间
- `payload` 是否能看出对应资源或操作信息

## 6. 建议记录的测试结论

每完成一轮项目测试，建议记录以下内容：

- 测试时间
- 项目名
- `project_id`
- 首个 `run_id`
- 是否生成成功
- 是否触发审批
- 是否成功续写第 2 章
- 是否存在明显内容质量问题
- 是否存在接口或页面错误

## 7. 常见异常与处理

### 7.1 `unauthorized`

说明：

- API Token 缺失或错误

处理：

1. 确认左侧 `API Token` 已填写
2. 再点一次 `保存配置`
3. 重新刷新页面

### 7.2 页面可开但生成失败

说明：

- 通常是上游模型、网络、输入数据或后端执行异常

处理：

1. 记录项目名、Run 时间、错误提示
2. 截图状态区与失败 Run
3. 通知运维侧查看容器日志

### 7.3 一直停留在运行中

说明：

- 真实模型模式下，单次链路可能较慢

处理：

1. 先等待 3 到 5 分钟
2. 若页面提示 `run_timeout`，不要重复狂点按钮
3. 记录当前 `run_id`，交由运维侧检查

### 7.4 无章节但有 Run

说明：

- 运行可能失败，或工件未完整生成

处理：

1. 点击 `查看工件`
2. 检查是否存在 `current_draft`、`publish_package`
3. 截图工件区和 Run 状态

## 8. 本轮通过标准

满足以下条件，可判定“当前版本具备初步公网实测条件”：

1. 公网入口、Basic Auth、API Token 三段鉴权均可正常使用。
2. 能成功创建项目并进入项目详情。
3. `生成章节` 可以快速返回并转入后台执行。
4. Run 完成后可查看完整工件。
5. 至少一轮审批链路可跑通。
6. 审批执行后可成功续写至第 2 章。
7. 审计日志能记录主要动作。

## 9. 问题反馈模板

建议按以下模板反馈问题：

```text
问题标题：
发生时间（UTC）：
项目名：
project_id：
run_id：
页面位置：
操作步骤：
实际结果：
预期结果：
截图或录屏：
是否可稳定复现：
```

## 10. 附录：快速命令

健康检查：

```bash
curl -u "<basic_user>:<basic_password>" \
  https://novel.jiamusoft.eu.cc/healthz
```

创建审批单：

```bash
curl -u "<basic_user>:<basic_password>" \
  -H "x-api-key: <api_token>" \
  -H "x-operator-id: editor-1" \
  -H "content-type: application/json" \
  -X POST \
  "https://novel.jiamusoft.eu.cc/api/runs/<run_id>/approval-requests" \
  -d '{
    "requested_action": "continue",
    "reason": "手工触发续写链路验证",
    "chapter_no": 1,
    "payload": {
      "source": "manual-alpha-test"
    }
  }'
```
