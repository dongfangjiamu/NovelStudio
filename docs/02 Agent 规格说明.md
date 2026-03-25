下面我直接把它收成一份可执行的 **“网文智能编辑部 v0.1”** 规格。

我先设一个默认场景，避免设计太空：  
**中文商业长篇连载**，单章 2000–4000 字，日更或双更，目标不是纯文学实验，而是“稳定更新、风格一致、剧情不断档、追读不断线”。

---

## 1. 先定三个原则

**第一，框架的核心不是多 agent，而是多工件。**  
真正该被管理的不是“谁在说话”，而是这些稳定产物：创作合同、设定集、角色卡、卷纲、章卡、Canon 状态表、问题单。

**第二，写作要像软件迭代，不像群聊。**  
不要让一群 agent 自由讨论到天荒地老。应该是：  
一个总控状态机 + 一组专职角色 + 一套验收门。

**第三，长篇创作必须把“记忆”独立出来。**  
代码有仓库和测试，网文必须有 **Canon DB**。  
谁在哪、知道什么、欠着哪些伏笔、战力到哪、感情关系推进到哪，这些不能靠上下文碰运气。

---

## 2. 角色设计：正式版 8 角

### 2.1 总编 / 编排器

它是唯一能推进状态的人。

职责很简单：发任务、收结果、过门禁、决定进入下一步还是打回。  
它**不写正文**，只写两种东西：`task_brief` 和 `phase_decision`。

它的权限边界也要很硬：  
不能偷偷改设定，不能私自改卷纲，不能替执笔者润色正文。

---

### 2.2 采访官 / 需求整理者

它把作者模糊想法，整理成一份 **创作合同**。

比如作者说：“我想写一本都市修仙爽文，男主前期苟，后期爆，女主别太工具人。”  
采访官不能只回一个优化 prompt，而要沉淀成明确字段：

- 面向平台和读者是谁
    
- 一句话卖点是什么
    
- 爽点密度高不高
    
- 感情线占比多少
    
- 文风偏朴素还是偏华丽
    
- 允许参考谁，不允许像谁
    
- 禁忌项是什么
    
- 更新节奏是什么
    

采访官的目标不是“理解用户”，而是**消灭模糊项**。

---

### 2.3 设定师

负责把创作合同翻译成 **Story Bible**。

它要定义的是硬设定，而不是漂亮废话。  
例如修仙文里，它必须写清楚：

- 力量体系如何分层
    
- 升级代价是什么
    
- 世界规则能不能破例
    
- 势力如何分布
    
- 哪些术语固定不能乱改
    

设定师不负责运行时记忆，只负责“立法”。

---

### 2.4 Canon 管理员

这是长期连载里最重要的角色之一。

它不负责创作，只负责维护 **运行时真相**。  
设定师负责“法律文本”，Canon 管理员负责“现实台账”。

它维护的不是优美文字，而是状态：

- 当前故事时间
    
- 角色位置
    
- 角色已知/未知信息
    
- 道具与伤势
    
- 关系变化
    
- 已埋伏笔与回收窗口
    
- 世界状态变化
    

正文通过验收之后，**只有它**可以把结果写回 Canon DB。

---

### 2.5 长纲师 / 卷纲师

负责三层规划：

- 整体主线
    
- 分卷目标
    
- 每卷关键转折
    

它不能只写“主角成长、反派变强、最后决战”这种空纲。  
每一卷至少要明确五件事：目标、障碍、升级、揭示、卷尾钩子。

正式运行时，我会要求它一次只规划到“卷级”，不要把 300 章一次性钉死。  
长篇连载更适合 **远程粗规划 + 近程细规划**。

---

### 2.6 章节策划

它只负责未来 3–5 章。

这是为了避免两个问题：  
一是规划过远导致僵死；二是每次重规划代价过大。

它的产物叫 **章卡**，每章都必须明确：

- 本章目标
    
- POV
    
- 关键冲突
    
- 信息增量
    
- 必须保留的爽点
    
- 禁止改动的 Canon 约束
    
- 章末钩子
    

---

### 2.7 执笔者（兼修订模式）

它只有两种模式：

**Draft 模式**：根据章卡写初稿。  
**Patch 模式**：根据问题单做定向修订。

这里我会强制一个限制：  
执笔者**不能擅自发明重大新设定**。  
一旦需要新增势力、规则、外挂、隐藏身份，必须提交变更申请，不能为了圆文临场创造。

这条规则很像软件里的“不要在实现层偷改需求”。

---

### 2.8 审校团

审校团不是一个 agent，而是一组并行子代理。至少四个：

**连贯性审校**：抓设定冲突、时间线、人设漂移、视角错误、因果断裂。  
**节奏审校**：抓推进、冲突强度、爽点密度、信息增量。  
**文风审校**：抓口吻、句式、对白一致性。  
**读者模拟器**：判断“这一章值不值得追”“付费点是否成立”。

注意一个关键边界：  
**审校团只报问题，不直接改正文。**  
否则最后会变成四五个 agent 一起重写，声音一定会散。

---

## 3. 工件定义：整个框架围绕这几份文件运转

### 3.1 创作合同 `creative_contract.yaml`

```yaml
project:
  working_title: ""
  platform: ""
  genre: ""
  subgenre: ""
  target_readers: []
  chapter_words_target: 3000
  total_words_target: 1200000
  update_cadence: "daily"

reader_promise:
  one_sentence_hook: ""
  core_emotional_payoff: ""
  primary_selling_points: []
  forbidden_elements: []

control_panel:
  pacing: 4          # 1-5，慢热到爆推进
 爽点_density: 4     # 1-5
  romance_weight: 2  # 1-5
  humor_weight: 2    # 1-5
  exposition_density: 2
  darkness_level: 2
  prose_flourish: 2  # 文风朴素-华丽

style:
  emulate: []
  avoid: []
  narration_style: ""
  dialogue_style: ""

non_negotiables:
  must_have: []
  must_not_have: []
```

这份合同相当于“需求规格说明书”。  
后面所有 agent 都要围绕它工作。

---

### 3.2 设定集 `story_bible.yaml`

```yaml
world:
  era: ""
  geography: []
  public_rules: []
  hidden_rules: []
  red_lines: []

power_system:
  levels: []
  costs: []
  bottlenecks: []
  exceptions_policy: "none"

factions:
  - name: ""
    goal: ""
    resources: []
    relationship_map: []

characters:
  - id: "mc"
    role: "protagonist"
    desire: ""
    fear: ""
    public_mask: ""
    hidden_truth: ""
    voiceprint: ""
    arc_start: ""
    arc_target: ""

terms:
  fixed_terms: []
  taboo_terms: []
```

---

### 3.3 Canon 状态表 `canon_state.yaml`

```yaml
story_clock:
  current_arc: 1
  current_chapter: 12
  in_story_time: "day_18"

character_states:
  mc:
    location: ""
    injuries: []
    inventory: []
    known_facts: []
    hidden_from_mc: []
    active_goals: []
    relationship_delta: []

world_state:
  faction_changes: []
  location_changes: []
  rule_exceptions_triggered: []

open_loops:
  - id: "F12"
    planted_in: 7
    description: ""
    expected_payoff_window: "12-20"
    status: "active"
```

这是长篇稳定性的关键。

---

### 3.4 章卡 `chapter_card.yaml`

```yaml
chapter_no: 13
arc: "卷一"
purpose: "让主角第一次意识到师门并不安全"
pov: "third_limited_mc"

entry_state:
  required_context: []
  emotional_state: ""
  unresolved_threads: []

scene_beats:
  - beat: 1
    goal: ""
    conflict: ""
    turn: ""
  - beat: 2
    goal: ""
    conflict: ""
    turn: ""

must_include:
  - ""
must_not_change:
  - "mc still does not know true identity of mentor"
  - "realm level remains Qi Refining 3"

hook:
  chapter_end_question: ""
  target_reader_impulse: "must_click_next"

word_count_target: 3200
```

---

### 3.5 问题单 `review_report.yaml`

```yaml
chapter_no: 13
decision: "rewrite"   # pass | rewrite | replan

scores:
  continuity: 78
  pacing: 84
  style: 76
  hook: 81
  total: 80

hard_violations:
  - "mentor reveals knowledge inconsistent with chapter 5 canon"

issues:
  - severity: "critical"
    type: "canon"
    evidence: "chapter 5 established mentor was absent from sect during incident"
    fix_instruction: "remove direct witness wording; convert to second-hand inference"

  - severity: "major"
    type: "motivation"
    evidence: "mc agrees too quickly"
    fix_instruction: "insert one hesitation beat tied to fear of expulsion"

  - severity: "minor"
    type: "style"
    evidence: "dialogue becomes too modern in paragraph 8"
    fix_instruction: "tone down slang"
```

---

## 4. 状态机：像 CI/CD 一样推进

我建议做成下面这个状态流：

```text
IDEA
 -> CONTRACT_DRAFT
 -> CONTRACT_LOCKED
 -> BIBLE_DRAFT
 -> BIBLE_LOCKED
 -> ARC_PLAN_DRAFT
 -> ARC_PLAN_LOCKED
 -> SPRINT_PLAN_READY        # 未来 3-5 章
 -> CHAPTER_CARD_READY
 -> DRAFTED
 -> REVIEWED
    -> PASS -> RELEASE_READY -> CANON_UPDATED -> FEEDBACK_INGESTED -> CHAPTER_CARD_READY
    -> REWRITE -> PATCH_DRAFTED -> REVIEWED
    -> REPLAN -> SPRINT_PLAN_READY
```

这里有三个设计点很重要。

**一，Lock 状态必须存在。**  
没有 lock，所有 agent 都会一边写一边改，最后没有任何东西是真正稳定的。

**二，重写和重规划要分开。**  
文句不顺、动机不足，是重写；  
设定冲突、章节目标本身错误，是重规划。

**三，Canon 更新必须在发布前后固定触发。**  
否则“实际发生过的剧情”不会沉淀回系统，越写越飘。

---

## 5. 验收门：什么时候过，什么时候打回

### Gate A：创作合同门

通过条件：

- 目标读者明确
    
- 一句话卖点明确
    
- 禁忌项明确
    
- 文风和平台不冲突
    
- 控制面板字段完整
    
- 没有高层矛盾
    

比如“想写轻松日常，但节奏想全程爆推进，还想悬疑烧脑，还想文风极度克制”，这种就是高层矛盾，不能过门。

---

### Gate B：设定门

通过条件：

- 力量系统可解释
    
- 世界规则无明显自冲突
    
- 主要势力和核心角色足够支撑前两卷
    
- 红线明确
    
- 术语固定
    

凡是依赖“到时候再编”的设定，尽量不放行。

---

### Gate C：卷纲门

通过条件：

- 每卷都有明确目标和对手
    
- 前三章内有入坑钩子
    
- 每卷末有转折或升级
    
- 伏笔有预计回收区间
    
- 主角成长线可追踪
    

---

### Gate D：章卡门

通过条件：

- 一章一个核心目的
    
- 一章至少一个有效冲突
    
- 一章至少一个信息增量
    
- 章末有追更驱动
    
- Canon 约束写清
    

---

### Gate E：正文门

我建议直接量化。

```text
pass:
  hard_violations == 0
  continuity >= 85
  pacing >= 80
  hook >= 80
  total >= 82

rewrite:
  hard_violations == 0
  total in [70, 81]
  or any single soft metric below threshold by <10

replan:
  hard_violations > 0
  or total < 70
  or 2+ major structural issues
```

这套分法的好处是：  
系统不会因为一句话不顺就退回大纲层，也不会因为设定冲突只做文案修补。

---

## 6. Prompt 骨架：每个角色都应该长这样

先给一个通用骨架，所有角色都按这个模板写。

```text
你是【角色名】。

目标：
- 用最少猜测完成本阶段任务。
- 严格遵守已锁定工件。
- 遇到冲突时不要自圆其说，输出 BLOCKER。

你可读取的工件：
- creative_contract
- story_bible
- canon_state
- arc_plan
- chapter_card
- last_chapter_summary
- review_report
（按角色裁剪）

优先级：
1. 用户最新明确指令
2. creative_contract（已锁定）
3. story_bible（已锁定）
4. canon_state（运行时真相）
5. arc_plan / chapter_card
6. style preferences

禁止：
- 擅自新增重大设定
- 擅自修改已锁定工件
- 输出无结构化结果
- 用“自行脑补”填补关键缺失

输出要求：
- 只输出指定 schema
- 不解释你的思路
- 不写角色外评论
```

下面给三个最关键角色的具体版。

---

### 6.1 执笔者 Prompt

```text
你是“执笔者”。

任务：
根据 chapter_card 写出本章正文初稿。
正文必须满足章卡目标、遵守 canon_state、保持既定文风。

你必须遵守：
- 不改变 must_not_change 列表
- 不新增重大设定
- 不提前揭示 canon_state 中隐藏信息
- 不为了顺畅而篡改角色动机

写作要求：
- 每 300-600 字至少产生一个微推进
- 对话要符合角色 voiceprint
- 结尾必须形成下一章驱动
- 允许局部发挥，但不得越过章卡边界

输出：
chapter_draft:
  title:
  summary_100w:
 正文:
  canon_delta_candidate:
  risk_notes:
```

---

### 6.2 连贯性审校 Prompt

```text
你是“连贯性审校”。

任务：
只检查以下问题：
- 设定冲突
- 时间线冲突
- 角色已知/未知信息错误
- 人设漂移
- POV 或因果错误

你不能做的事：
- 不评价文采
- 不建议全面重写
- 不替作者改文

输出：
review_report:
  decision:
  continuity_score:
  hard_violations:
  issues:
    - severity:
      type:
      evidence:
      fix_instruction:
```

---

### 6.3 总编 / 编排器 Prompt

```text
你是“总编/编排器”。

任务：
读取所有 review_report，合并分歧，做阶段决策：
- pass
- rewrite
- replan

裁决原则：
- 硬违规优先
- 结构问题优先于文句问题
- 连载稳定性优先于局部炫技
- 已锁定工件不可被下游偷偷覆盖

输出：
phase_decision:
  final_decision:
  must_fix:
  can_defer:
  next_owner:
  artifact_updates:
```

---

## 7. 编排逻辑：真正执行时怎么跑

用伪代码写，大概就是这样：

```python
contract = intake_agent(user_brief)
assert gate_contract(contract)

bible = lore_agent(contract)
assert gate_bible(bible)

arc_plan = arc_planner(contract, bible)
assert gate_arc(arc_plan)

canon_state = init_canon(contract, bible, arc_plan)

while not story_finished:
    sprint = chapter_planner(contract, bible, canon_state, arc_plan, window=3)

    for chapter_card in sprint:
        draft = writer(contract, bible, canon_state, chapter_card)

        reviews = parallel_run([
            continuity_reviewer(draft, contract, bible, canon_state, chapter_card),
            pacing_reviewer(draft, contract, chapter_card),
            style_reviewer(draft, contract),
            reader_simulator(draft, contract, chapter_card)
        ])

        decision = chief_editor(reviews)

        if decision == "pass":
            publish_package = release_prepare(draft)
            canon_state = canon_update(canon_state, draft)
            feedback_buffer = ingest_feedback()
        elif decision == "rewrite":
            draft = writer_patch(draft, reviews, contract, bible, canon_state, chapter_card)
            repeat review
        else:
            sprint = replan_next_chapters(contract, bible, canon_state, arc_plan, reviews)
            break
```

这里最关键的不是并行，而是 **谁能改什么**。  
权限不清，框架一定崩。

---

## 8. 为了让结果符合预期，我会再加四个硬规则

### 8.1 所有变更都走 CR（Change Request）

任何重大新增都必须提交 `change_request.yaml`。

比如：

- 新增外挂
    
- 改主角底层目标
    
- 提前揭露大反派身份
    
- 更改力量系统例外规则
    

没有 CR，就不能写进正文。

---

### 8.2 永远不要把“整本书全文”直接塞给执笔者

真正稳的做法是 **上下文分层检索**：

执笔者只拿到：

- 创作合同摘要
    
- 本章相关设定摘录
    
- 角色卡关键字段
    
- Canon 当前状态
    
- 最近 1–2 章摘要
    
- 当前章卡
    

不要把 200 章原文全塞进去。  
那样不是“信息更全”，而是“噪声更大”。

---

### 8.3 重要章节允许双草稿

这些章节可以并行出两个版本：

- 上架点
    
- 卷末高潮
    
- 大反转
    
- 告白/决裂
    
- 大战首秀
    

一个版本偏稳，一个版本偏猛。  
再交给总编和审校选。  
这种 A/B 机制，在网文里非常值。

---

### 8.4 只允许一个“最终声音”

我建议长期连载里，**只有一个执笔者**负责最终文字输出。  
其他 agent 负责规划、校验、诊断，不负责形成最终 prose。

原因很简单：  
多 writer 轮流上阵，最容易死的就是文风统一。

---

## 9. 最小上线版本：别一开始就做太复杂

如果你真想先做第一版，我建议只上线这 6 个节点：

**采访官 → 设定师 → 长纲师 → 章节策划 → 执笔者 → 审校团**

同时只维护 4 个工件：

**创作合同、设定集、章卡、Canon 状态表**

先不要上评论回流，不要上复杂运营代理，也不要一上来做“自动日更 300 万字”。  
先跑通下面这个闭环：

**明确需求 → 锁设定 → 生成章卡 → 写一章 → 审一章 → 更新 Canon**

只要这个闭环稳定，后面加卷纲重规划、读者反馈回流、A/B 草稿，都很自然。

---

## 10. 一句话总结这套框架的本质

在软件工程里，成熟框架靠的是：**角色分工 + 工件管理 + 状态流转 + 验收门**。  
网文创作也一样。

真正靠谱的方向不是“让很多 agent 一起写小说”，而是：

**让一个智能编辑部，围绕一套稳定工件，去管理一位稳定执笔者。**

下一步最实用的是把这份规格直接翻成两份东西：  
一份 **LangGraph / 工作流节点图**，一份 **每个角色可直接运行的 system prompt + JSON Schema**。