const state = {
  projects: [],
  selectedProjectId: null,
  selectedRunId: null,
  projectSnapshot: {
    chapters: [],
    runs: [],
    approvals: [],
  },
  apiToken: localStorage.getItem("novelstudio_api_token") || "",
  operatorId: localStorage.getItem("novelstudio_operator_id") || "editor-1",
};

const el = {
  apiToken: document.getElementById("api-token"),
  operatorId: document.getElementById("operator-id"),
  saveAuth: document.getElementById("save-auth"),
  refreshProjects: document.getElementById("refresh-projects"),
  refreshAudit: document.getElementById("refresh-audit"),
  projectsList: document.getElementById("projects-list"),
  chaptersList: document.getElementById("chapters-list"),
  runsList: document.getElementById("runs-list"),
  approvalsList: document.getElementById("approvals-list"),
  artifactsList: document.getElementById("artifacts-list"),
  auditList: document.getElementById("audit-list"),
  createRun: document.getElementById("create-run"),
  projectForm: document.getElementById("project-form"),
  projectTitle: document.getElementById("project-title"),
  projectMeta: document.getElementById("project-meta"),
  summaryGoal: document.getElementById("summary-goal"),
  summarySystem: document.getElementById("summary-system"),
  summaryEvent: document.getElementById("summary-event"),
  summaryNext: document.getElementById("summary-next"),
  focusRunCaption: document.getElementById("focus-run-caption"),
  focusRun: document.getElementById("focus-run"),
  selectedRunLabel: document.getElementById("selected-run-label"),
  statusPill: document.getElementById("status-pill"),
  heroNote: document.getElementById("hero-note"),
  overviewStage: document.getElementById("overview-stage"),
  overviewChapter: document.getElementById("overview-chapter"),
  overviewBlocker: document.getElementById("overview-blocker"),
  overviewAction: document.getElementById("overview-action"),
  actionTitle: document.getElementById("action-title"),
  actionBody: document.getElementById("action-body"),
};

const STATUS_LABELS = {
  running: "生成中",
  awaiting_approval: "等待审批",
  failed: "已失败",
  completed: "已完成",
  pending: "待处理",
  approved: "已通过",
  rejected: "已驳回",
};

const NODE_LABELS = {
  interviewer_contract: "整理创作约束",
  lore_builder: "建立设定",
  arc_planner: "规划卷纲",
  chapter_planner: "生成章卡",
  draft_writer: "写初稿",
  patch_writer: "修稿",
  continuity_reviewer: "连续性审校",
  pacing_reviewer: "节奏审校",
  style_reviewer: "文风审校",
  reader_simulator: "读者模拟",
  chief_editor: "主编汇总",
  release_prepare: "整理发布包",
  canon_commit: "回写 Canon",
  feedback_ingest: "回收结果",
  human_gate: "等待人工处理",
};

const ARTIFACT_LABELS = {
  creative_contract: "创作契约",
  story_bible: "故事设定",
  arc_plan: "卷纲规划",
  current_card: "当前章卡",
  current_draft: "当前正文草稿",
  phase_decision: "阶段决策",
  publish_package: "发布包",
  canon_state: "Canon 状态",
  feedback_summary: "反馈摘要",
  latest_review_reports: "审校结果",
  human_guidance: "人工指导",
  blockers: "阻塞原因",
  event_log: "事件日志",
};

const ARTIFACT_ORDER = [
  "publish_package",
  "current_draft",
  "current_card",
  "latest_review_reports",
  "phase_decision",
  "human_guidance",
  "creative_contract",
  "story_bible",
  "arc_plan",
  "canon_state",
  "feedback_summary",
  "blockers",
  "event_log",
];

const EVENT_LABELS = {
  run_started: "开始运行",
  creative_contract_ready: "创作契约已生成",
  story_bible_ready: "故事设定已生成",
  arc_plan_ready: "卷纲已生成",
  chapter_card_ready: "章卡已生成",
  chapter_draft_ready: "正文草稿已生成",
  review_ready: "审校结果已返回",
  release_ready: "发布包已整理",
  canon_updated: "Canon 已更新",
  feedback_ingested: "结果已回收",
  manual_fail: "人工标记失败",
  auto_timeout: "系统自动判定超时",
};

function setStatus(text, kind = "ready") {
  el.statusPill.textContent = text;
  el.statusPill.style.color = kind === "error" ? "#9b1c1c" : kind === "warn" ? "#8d5b00" : "#1f6b44";
  el.statusPill.style.background = kind === "error" ? "rgba(155,28,28,0.12)" : kind === "warn" ? "rgba(141,91,0,0.12)" : "rgba(31,107,68,0.12)";
}

function headers() {
  const value = { "content-type": "application/json", "x-operator-id": state.operatorId };
  if (state.apiToken) {
    value["x-api-key"] = state.apiToken;
  }
  return value;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      ...headers(),
      ...(options.headers || {}),
    },
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  if (!response.ok) {
    throw new Error(data?.detail || `request_failed:${response.status}`);
  }
  return data;
}

function card(title, meta, actions = [], extra = "") {
  const actionsHtml = actions.length
    ? `<div class="actions">${actions
        .map((item) => `<button class="button ghost" data-action="${item.action}" data-id="${item.id}">${item.label}</button>`)
        .join("")}</div>`
    : "";
  return `<div class="card"><h4>${title}</h4><div class="meta">${meta}</div>${extra}${actionsHtml}</div>`;
}

function statusChip(status) {
  return `<span class="status-chip status-${status}">${STATUS_LABELS[status] || status}</span>`;
}

function formatTimestamp(value) {
  if (!value) return "未记录";
  const stamp = new Date(value);
  if (Number.isNaN(stamp.getTime())) return value;
  return stamp.toLocaleString("zh-CN", {
    hour12: false,
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function formatDuration(ms) {
  if (!Number.isFinite(ms) || ms <= 0) return "刚刚";
  const totalSeconds = Math.floor(ms / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  if (hours > 0) return `${hours}小时${minutes}分`;
  if (minutes > 0) return `${minutes}分${seconds}秒`;
  return `${seconds}秒`;
}

function selectedProject() {
  return state.projects.find((item) => item.project_id === state.selectedProjectId) || null;
}

function nodeLabel(value) {
  return NODE_LABELS[value] || value || "未记录";
}

function artifactLabel(value) {
  return ARTIFACT_LABELS[value] || value;
}

function eventLabel(value) {
  if (!value) return "暂无事件";
  const [kind, detail, extra] = String(value).split(":");
  if (kind === "chapter_card_ready" && detail) return `第 ${detail} 章章卡已生成`;
  if (kind === "review_ready" && detail && extra) return `${nodeLabel(`${detail}_reviewer`)}：${extra === "pass" ? "通过" : extra === "rewrite" ? "建议重写" : extra}`;
  return EVENT_LABELS[kind] || value;
}

function buildTimelineEntries(run) {
  const progress = run.result?.progress || {};
  const entries = [];
  entries.push({
    title: "开始生成",
    meta: formatTimestamp(run.created_at),
    status: "done",
  });
  (progress.event_log_tail || []).forEach((item) => {
    entries.push({
      title: eventLabel(item),
      meta: formatTimestamp(progress.updated_at),
      status: item === progress.latest_event ? "current" : "done",
    });
  });
  if (run.status === "running") {
    entries.push({
      title: `正在进行：${nodeLabel(progress.current_node)}`,
      meta: `已等待 ${formatDuration((progress.stalled_for_seconds || 0) * 1000)}`,
      status: "current",
    });
  }
  if (run.status === "failed") {
    entries.push({
      title: "本次运行已结束为失败",
      meta: run.error || "已停止",
      status: "failed",
    });
  }
  if (run.status === "completed") {
    entries.push({
      title: "本次运行已完成",
      meta: formatTimestamp(run.finished_at),
      status: "done",
    });
  }
  return entries;
}

function parseListField(value) {
  return String(value || "")
    .split(/\n|,/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function latestChapterNo(chapters) {
  return chapters.reduce((max, item) => Math.max(max, item.chapter_no || 0), 0);
}

function pickFocusRun(runs) {
  if (!runs.length) return null;
  const priority = {
    running: 0,
    awaiting_approval: 1,
    failed: 2,
    completed: 3,
  };
  return [...runs].sort((left, right) => {
    const byStatus = (priority[left.status] ?? 99) - (priority[right.status] ?? 99);
    if (byStatus !== 0) return byStatus;
    return right.created_at.localeCompare(left.created_at);
  })[0];
}

function upsertRunSnapshot(run) {
  const others = state.projectSnapshot.runs.filter((item) => item.run_id !== run.run_id);
  state.projectSnapshot.runs = [run, ...others].sort((left, right) => right.created_at.localeCompare(left.created_at));
}

function deriveSummary(project, snapshot) {
  const chapters = snapshot.chapters || [];
  const runs = snapshot.runs || [];
  const approvals = snapshot.approvals || [];
  const focusRun = pickFocusRun(runs);
  const pendingApproval = approvals.find((item) => item.status === "pending");
  const approvedWaitingExecution = approvals.find((item) => item.status === "approved" && !item.executed_run_id);
  const latestChapter = latestChapterNo(chapters);
  const progress = focusRun?.result?.progress || {};
  const updatedAt = progress.updated_at ? formatTimestamp(progress.updated_at) : "未记录";
  const stageGoal = progress.stage_goal || "等待下一步目标。";
  const possibleCause = progress.possible_cause || null;
  const interventionAction = focusRun?.result?.manual_intervention?.action || null;

  if (!project) {
    return {
      goal: "先选择项目，或先创建一个新项目。",
      system: "系统空闲。",
      event: "还没有选定目标项目。",
      next: "在左侧选择项目，或在“新建项目”区域创建一个项目。",
      heroNote: "先确认你要继续写的项目，再进行生成。系统会尽量把推荐动作放在最显眼的位置。",
      pill: "等待选择项目",
      kind: "ready",
      focusRun: null,
      disableRunButton: true,
      runButtonLabel: "生成章节",
    };
  }

  if (focusRun?.status === "running") {
    const targetChapter = progress.chapter_no || latestChapter + 1 || 1;
    const currentNode = progress.current_node || "等待节点反馈";
    const latestEvent = progress.latest_event || "run_started";
    const staleMs = progress.updated_at ? Date.now() - new Date(progress.updated_at).getTime() : 0;
    const stale = staleMs > 180000;
    return {
      goal: `完成第 ${targetChapter} 章的生成。`,
      system: `系统正在后台执行，当前节点是 ${currentNode}；当前目标是：${stageGoal}`,
      event: `最近事件：${latestEvent}；最近更新时间：${updatedAt}；当前重写次数：${progress.rewrite_count ?? 0}。`,
      next: stale
        ? `这条 Run 已经 ${formatDuration(staleMs)} 没有新进度。它更像是卡住，而不是一直重写。先点“刷新”确认；如果仍不动，就点“标记失败”，然后再“重新尝试”。`
        : `当前已经有 Run 在执行，不要重复点击“生成章节”。等待自动刷新，或点“查看工件”跟踪当前 Run。`,
      heroNote: stale
        ? "系统判断这条运行更像是卡住，而不是正常生成中。建议先收口这条失败，再决定是否重试。"
        : "当前已经在写作流程中。你现在最需要做的是观察，不是重复点击。",
      pill: stale ? `Run 可能卡住: ${focusRun.run_id}` : `Run 执行中: ${currentNode}`,
      kind: "warn",
      focusRun,
      disableRunButton: true,
      runButtonLabel: "生成中…",
    };
  }

  if (pendingApproval) {
    return {
      goal: "决定当前章节是否通过人工审批。",
      system: "系统已暂停，等待人工决定。",
      event: `待处理审批：${pendingApproval.reason}`,
      next: "去“审批”栏点击“通过”或“驳回”。如果通过后要继续写下一章，再点击“执行”。",
      heroNote: "现在系统不会继续自动写。你做出审批决定后，它才会进入下一步。",
      pill: "等待人工审批",
      kind: "warn",
      focusRun: focusRun || null,
      disableRunButton: true,
      runButtonLabel: "等待审批",
    };
  }

  if (approvedWaitingExecution) {
    return {
      goal: "启动已审批通过的续写任务。",
      system: "系统等待你执行下一步续写。",
      event: `审批已通过，但尚未执行：${approvedWaitingExecution.approval_id}`,
      next: "在“审批”栏点击“执行”，启动下一条后台 Run。",
      heroNote: "审批已经通过，但还没有开始续写。这里最重要的是启动下一条运行。",
      pill: "等待执行续写",
      kind: "warn",
      focusRun: focusRun || null,
      disableRunButton: true,
      runButtonLabel: "等待执行",
    };
  }

  if (focusRun?.status === "failed") {
    return {
      goal: `重新尝试生成第 ${progress.chapter_no || latestChapter + 1 || 1} 章。`,
      system: "上一条 Run 已失败，系统目前空闲。",
      event: focusRun.error ? `失败原因：${focusRun.error}` : `失败 Run：${focusRun.run_id}`,
      next: interventionAction === "auto_timeout"
        ? "系统已经自动把长时间无进度的运行收口成失败。先看过程材料，再决定是否点“重新尝试”。"
        : "优先处理这条最新失败记录。先查看工件确认问题，再决定是否点“重新尝试”。更老的失败记录默认只作参考。",
      heroNote: interventionAction === "auto_timeout"
        ? "这条运行不是你手动终止的，而是系统自动判定它超时并收口。现在你只需要决定是否重试。"
        : "你不需要把所有失败记录都重新点一遍。通常只处理最新那条失败记录。",
      pill: "上一条 Run 失败",
      kind: "error",
      focusRun,
      disableRunButton: false,
      runButtonLabel: "重新生成章节",
    };
  }

  if (latestChapter > 0) {
    return {
      goal: `复核已生成的第 ${latestChapter} 章结果。`,
      system: "系统空闲，最近一次 Run 已完成。",
      event: `最近已生成到第 ${latestChapter} 章。`,
      next: "先查看当前章节工件和审校结果；如果没有待审批项且你想继续，可以再次点击“生成章节”。",
      heroNote: "当前没有阻塞。你可以先复核结果，再决定是否继续写下一章。",
      pill: "最近 Run 已完成",
      kind: "ready",
      focusRun,
      disableRunButton: false,
      runButtonLabel: "继续生成章节",
    };
  }

  return {
    goal: "启动首章生成。",
    system: "系统空闲。",
    event: "项目已创建，但还没有任何章节和 Run。",
    next: "点击“生成章节”，启动第一个后台 Run。",
    heroNote: "这是一个全新项目。先跑出第 1 章，再看系统给出的材料和建议。",
    pill: "可以开始生成",
    kind: "ready",
    focusRun: null,
    disableRunButton: false,
    runButtonLabel: "生成章节",
  };
}

function renderSummary(summary) {
  el.summaryGoal.textContent = summary.goal;
  el.summarySystem.textContent = summary.system;
  el.summaryEvent.textContent = summary.event;
  el.summaryNext.textContent = summary.next;
  el.heroNote.textContent = summary.heroNote || "系统会尽量直接告诉你：现在在做什么、为什么停住了、下一步该点哪里。";
  el.actionTitle.textContent = summary.goal;
  el.actionBody.textContent = summary.next;
  setStatus(summary.pill, summary.kind);
  el.createRun.disabled = summary.disableRunButton;
  el.createRun.textContent = summary.runButtonLabel;
}

function renderOverview(project, snapshot, summary) {
  const chapters = snapshot.chapters || [];
  const focusRun = summary.focusRun;
  el.overviewStage.textContent = !project
    ? "等待选择项目"
    : focusRun?.status === "running"
      ? "写作中"
      : focusRun?.status === "awaiting_approval"
        ? "等待审批"
        : focusRun?.status === "failed"
          ? "需要补救"
          : chapters.length
            ? "已有章节成果"
            : "尚未启动";
  el.overviewChapter.textContent = chapters.length ? `已生成到第 ${latestChapterNo(chapters)} 章` : "尚未生成章节";
  el.overviewBlocker.textContent = focusRun?.status === "failed"
    ? "最新运行失败"
    : focusRun?.status === "awaiting_approval"
      ? "等待人工审批"
      : focusRun?.status === "running"
        ? "无，需要等待"
        : "暂无明显阻塞";
  el.overviewAction.textContent = summary.next;
}

function renderFocusRun(summary) {
  const run = summary.focusRun;
  if (!run) {
    el.focusRunCaption.textContent = "暂无活跃 Run";
    el.focusRun.innerHTML = `<div class="empty">当前没有需要重点关注的 Run。</div>`;
    return;
  }

  const progress = run.result?.progress || {};
  const logTail = progress.event_log_tail || [];
  const latestEvent = progress.latest_event || "暂无事件";
  const updatedAt = progress.updated_at || run.created_at;
  const staleMs = updatedAt ? Date.now() - new Date(updatedAt).getTime() : 0;
  const staleLabel = staleMs > 0 ? formatDuration(staleMs) : "未记录";
  const currentNode = nodeLabel(progress.current_node);
  const stageGoal = progress.stage_goal || "未记录";
  const possibleCause = progress.possible_cause;
  const intervention = run.result?.manual_intervention || null;
  const timelineEntries = buildTimelineEntries(run);
  const errorBlock = run.error
    ? `<div class="focus-metric"><strong class="error-copy">错误</strong><div class="meta">${run.error}</div></div>`
    : "";
  const causeBlock = possibleCause
    ? `<div class="focus-metric"><strong>可能原因</strong><div class="meta warning-copy">${possibleCause}</div></div>`
    : "";
  const interventionBlock = intervention
    ? `<div class="focus-metric"><strong>系统处理</strong><div class="meta">${intervention.action === "auto_timeout" ? "系统已自动收口这条超时运行" : "这条运行已被人工收口"}</div></div>`
    : "";
  const actionButtons = [
    `<button class="button ghost" data-action="view-run" data-id="${run.run_id}">查看工件</button>`,
  ];
  if (run.status === "running") {
    actionButtons.push(`<button class="button ghost" data-action="mark-failed" data-id="${run.run_id}">标记失败</button>`);
  }
  if (run.status === "failed") {
    actionButtons.push(`<button class="button ghost" data-action="retry-run" data-id="${run.run_id}">重新尝试</button>`);
  }

  el.focusRunCaption.textContent = `${run.run_id} · ${STATUS_LABELS[run.status] || run.status}`;
  el.focusRun.innerHTML = `
    <div class="focus-run-grid">
      <div class="focus-metric">
        <strong>Run</strong>
        <div class="meta">${run.run_id}</div>
      </div>
      <div class="focus-metric">
        <strong>状态</strong>
        <div class="meta">${statusChip(run.status)}</div>
      </div>
      <div class="focus-metric">
        <strong>当前节点</strong>
        <div class="meta">${currentNode}</div>
      </div>
      <div class="focus-metric">
        <strong>最近更新时间</strong>
        <div class="meta">${formatTimestamp(updatedAt)}</div>
      </div>
      <div class="focus-metric">
        <strong>最新事件</strong>
        <div class="meta">${latestEvent}</div>
      </div>
      <div class="focus-metric">
        <strong>目标章节</strong>
        <div class="meta">第 ${progress.chapter_no || latestChapterNo(state.projectSnapshot.chapters) + 1 || 1} 章</div>
      </div>
      <div class="focus-metric">
        <strong>重写次数</strong>
        <div class="meta">${progress.rewrite_count ?? 0}</div>
      </div>
      <div class="focus-metric">
        <strong>静止时长</strong>
        <div class="meta">${staleLabel}</div>
      </div>
      <div class="focus-metric">
        <strong>阶段决策</strong>
        <div class="meta">${progress.phase_decision || "未记录"}</div>
      </div>
      <div class="focus-metric">
        <strong>当前目标</strong>
        <div class="meta">${stageGoal}</div>
      </div>
      ${interventionBlock}
      ${causeBlock}
      ${errorBlock}
    </div>
    <div class="card">
      <div class="card-head">
        <h4>阶段时间线</h4>
        ${statusChip(run.status)}
      </div>
      <div class="timeline">
        ${timelineEntries
          .map(
            (entry) => `
              <div class="timeline-item timeline-${entry.status}">
                <div class="timeline-dot"></div>
                <div>
                  <div class="timeline-title">${entry.title}</div>
                  <div class="meta">${entry.meta}</div>
                </div>
              </div>
            `
          )
          .join("")}
      </div>
    </div>
    <div class="card">
      <div class="card-head">
        <h4>最近事件尾部</h4>
        ${statusChip(run.status)}
      </div>
      <div class="meta">${logTail.length ? logTail.join(" -> ") : "暂无事件日志"}</div>
      <div class="actions">
        ${actionButtons.join("")}
      </div>
    </div>
  `;
  el.focusRun.querySelectorAll("[data-action]").forEach((node) => {
    node.addEventListener("click", () => handleRunAction(node.dataset.action, node.dataset.id));
  });
}

function renderProjectState() {
  const project = selectedProject();
  const snapshot = state.projectSnapshot;
  renderChapters(snapshot.chapters || []);
  const focusRunId = pickFocusRun(snapshot.runs || [])?.run_id || null;
  const summary = deriveSummary(project, snapshot);
  renderOverview(project, snapshot, summary);
  renderRuns(snapshot.runs || [], focusRunId);
  renderApprovals(snapshot.approvals || []);
  renderSummary(summary);
  renderFocusRun(summary);
}

function renderProjects() {
  if (!state.projects.length) {
    el.projectsList.innerHTML = `<div class="empty">还没有项目</div>`;
    return;
  }
  el.projectsList.innerHTML = state.projects
    .map((project) => {
      const active = project.project_id === state.selectedProjectId ? "active" : "";
      return `<button class="card ${active}" data-project-id="${project.project_id}">
        <h4>${project.name}</h4>
        <div class="meta">${formatTimestamp(project.created_at)} · ${project.project_id}</div>
      </button>`;
    })
    .join("");
  el.projectsList.querySelectorAll("[data-project-id]").forEach((node) => {
    node.addEventListener("click", () => selectProject(node.dataset.projectId));
  });
}

function renderChapters(chapters) {
  el.chaptersList.innerHTML = chapters.length
    ? chapters
        .slice()
        .sort((left, right) => right.chapter_no - left.chapter_no)
        .map((item) => card(`第 ${item.chapter_no} 章`, `${item.title}<br>${STATUS_LABELS[item.status] || item.status}`))
        .join("")
    : `<div class="empty">暂无章节</div>`;
}

function renderRuns(runs, focusRunId) {
  if (!runs.length) {
    el.runsList.innerHTML = `<div class="empty">暂无运行记录</div>`;
    return;
  }

  const recommended = [];
  const history = [];
  runs.forEach((item) => {
    if (item.run_id === focusRunId) {
      recommended.push(item);
    } else {
      history.push(item);
    }
  });

  const renderRunCard = (item, { recommendedCard = false } = {}) => {
    const progress = item.result?.progress || {};
    const updatedAt = progress.updated_at || item.created_at;
    const marker = item.status === "running"
      ? progress.latest_event || nodeLabel(progress.current_node) || "等待反馈"
      : item.error || progress.latest_event || "无附加信息";
    const classes = ["card"];
    if (item.run_id === state.selectedRunId || item.run_id === focusRunId) classes.push("active-run");
    if (recommendedCard) classes.push("recommended");
    if (!recommendedCard) classes.push("history");
    const actions = [`<button class="button ghost" data-action="view-run" data-id="${item.run_id}">查看工件</button>`];
    if (recommendedCard && item.status === "running") {
      actions.push(`<button class="button ghost" data-action="mark-failed" data-id="${item.run_id}">标记失败</button>`);
    }
    if (recommendedCard && item.status === "failed") {
      actions.push(`<button class="button ghost" data-action="retry-run" data-id="${item.run_id}">重新尝试</button>`);
    }
    const caption = recommendedCard
      ? "这是当前最值得处理的一条运行记录。"
      : item.status === "failed"
        ? (item.result?.manual_intervention?.action === "auto_timeout"
            ? "历史超时记录，系统已经自动收口，默认只用于参考。"
            : "历史失败记录，默认只用于参考，不建议优先再次重试。")
        : "历史记录，可随时查看过程材料。";
    return `
      <div class="${classes.join(" ")}">
        <div class="card-head">
          <h4>${item.run_id}</h4>
          ${statusChip(item.status)}
        </div>
        <div class="meta">创建于 ${formatTimestamp(item.created_at)}</div>
        <div class="meta">最近更新 ${formatTimestamp(updatedAt)} · 重写 ${progress.rewrite_count ?? 0} 次</div>
        <div class="meta">${marker}</div>
        <div class="card-caption">${caption}</div>
        <div class="actions">
          ${actions.join("")}
        </div>
      </div>
    `;
  };

  const blocks = [];
  if (recommended.length) {
    blocks.push(`<div class="section-caption">当前推荐处理</div>`);
    blocks.push(recommended.map((item) => renderRunCard(item, { recommendedCard: true })).join(""));
  }
  if (history.length) {
    blocks.push(`<div class="section-caption">历史记录</div>`);
    blocks.push(history.map((item) => renderRunCard(item)).join(""));
  }
  el.runsList.innerHTML = blocks.join("");
  el.runsList.querySelectorAll("[data-action]").forEach((node) => {
    node.addEventListener("click", () => handleRunAction(node.dataset.action, node.dataset.id));
  });
}

function renderApprovals(items) {
  el.approvalsList.innerHTML = items.length
    ? items
        .map((item) => {
          const actions = [];
          if (item.status === "pending") {
            actions.push({ action: "approve", id: item.approval_id, label: "通过" });
            actions.push({ action: "reject", id: item.approval_id, label: "驳回" });
          }
          if (item.status === "approved" && !item.executed_run_id) {
            actions.push({ action: "execute", id: item.approval_id, label: "执行" });
          }
          return card(
            item.requested_action === "continue" ? "继续写下一章" : item.requested_action,
            `${STATUS_LABELS[item.status] || item.status}<br>${item.reason}`,
            actions,
            item.executed_run_id ? `<div class="meta">executed: ${item.executed_run_id}</div>` : ""
          );
        })
        .join("")
    : `<div class="empty">暂无审批单</div>`;
  el.approvalsList.querySelectorAll("[data-action]").forEach((node) => {
    node.addEventListener("click", () => handleApprovalAction(node.dataset.action, node.dataset.id));
  });
}

function renderArtifacts(items) {
  if (!items.length) {
    el.artifactsList.innerHTML = `<div class="empty">当前还没有可展示的过程材料</div>`;
    return;
  }

  const sorted = [...items].sort((left, right) => {
    const leftRank = ARTIFACT_ORDER.indexOf(left.artifact_type);
    const rightRank = ARTIFACT_ORDER.indexOf(right.artifact_type);
    return (leftRank === -1 ? 999 : leftRank) - (rightRank === -1 ? 999 : rightRank);
  });

  el.artifactsList.innerHTML = sorted
    .map((item) => {
      const hint = item.artifact_type === "publish_package"
        ? "这是最接近对外可读结果的版本。"
        : item.artifact_type === "current_draft"
          ? "这是当前章节的正文草稿。"
          : item.artifact_type === "current_card"
            ? "这是系统准备写这一章前的章卡。"
            : item.artifact_type === "latest_review_reports"
              ? "这里能看到系统为什么判定通过、重写或重规划。"
              : "这是流程中的中间材料。";
      return `
        <div class="card artifact-card">
          <h4>${artifactLabel(item.artifact_type)}</h4>
          <div class="meta">${formatTimestamp(item.created_at)}</div>
          <div class="card-caption">${hint}</div>
          <pre>${JSON.stringify(item.payload, null, 2)}</pre>
        </div>
      `;
    })
    .join("");
}

function renderAudit(items) {
  el.auditList.innerHTML = items.length
    ? items
        .map((item) => card(item.action, `${item.actor}<br>${item.created_at}`, [], `<pre>${JSON.stringify(item.payload, null, 2)}</pre>`))
        .join("")
    : `<div class="empty">暂无审计日志</div>`;
}

async function loadProjects() {
  setStatus("正在加载项目…");
  state.projects = (await api("/api/projects")).sort((left, right) => right.created_at.localeCompare(left.created_at));
  renderProjects();
  if (!state.selectedProjectId && state.projects.length) {
    await selectProject(state.projects[0].project_id);
    return;
  }
  if (!state.selectedProjectId) {
    renderSummary(deriveSummary(null, state.projectSnapshot));
    renderFocusRun(deriveSummary(null, state.projectSnapshot));
  }
}

async function selectProject(projectId) {
  state.selectedProjectId = projectId;
  renderProjects();
  const project = state.projects.find((item) => item.project_id === projectId);
  el.projectTitle.textContent = project?.name || "未选择项目";
  el.projectMeta.textContent = project ? `${project.project_id}` : "选择左侧项目后查看详情";
  if (!project) {
    renderProjectState();
    return;
  }

  const [chapters, runs, approvals] = await Promise.all([
    api(`/api/projects/${projectId}/chapters`),
    api(`/api/projects/${projectId}/runs`),
    api(`/api/projects/${projectId}/approval-requests`),
  ]);
  state.projectSnapshot = { chapters, runs, approvals };
  const knownRun = runs.find((item) => item.run_id === state.selectedRunId);
  if (!knownRun) {
    state.selectedRunId = pickFocusRun(runs)?.run_id || null;
  }
  renderProjectState();
  if (state.selectedRunId) {
    await loadArtifacts(state.selectedRunId);
  } else {
    el.selectedRunLabel.textContent = "未选择 Run";
    renderArtifacts([]);
  }
}

async function loadArtifacts(runId) {
  state.selectedRunId = runId;
  el.selectedRunLabel.textContent = runId;
  const artifacts = await api(`/api/runs/${runId}/artifacts`);
  renderArtifacts(artifacts);
  renderProjectState();
}

async function handleRunAction(action, runId) {
  if (action === "view-run") {
    await loadArtifacts(runId);
    return;
  }

  if (action === "mark-failed") {
    if (!window.confirm(`确认把 ${runId} 标记为失败吗？这不会强杀上游请求，但会停止把它当成有效 Run。`)) {
      return;
    }
    try {
      await api(`/api/runs/${runId}/mark-failed`, { method: "POST" });
      await selectProject(state.selectedProjectId);
      await loadAudit();
      if (state.selectedRunId === runId) {
        await loadArtifacts(runId);
      }
      setStatus(`已将 ${runId} 标记为失败，可重新尝试。`, "warn");
    } catch (error) {
      setStatus(String(error.message || error), "error");
    }
    return;
  }

  if (action === "retry-run") {
    try {
      const payload = await api(`/api/runs/${runId}/retry`, { method: "POST" });
      state.selectedRunId = payload.run_id;
      await selectProject(state.selectedProjectId);
      const completedRun = await waitForRunCompletion(payload.run_id);
      await selectProject(state.selectedProjectId);
      await loadAudit();
      if (completedRun) {
        setStatus(`重试 Run 已完成: ${payload.run_id}`);
      } else {
        setStatus(`重试 Run 仍在后台执行，可稍后刷新查看: ${payload.run_id}`, "warn");
      }
    } catch (error) {
      setStatus(String(error.message || error), "error");
    }
  }
}

async function loadAudit() {
  const logs = await api("/api/audit-logs?limit=20");
  renderAudit(logs);
}

async function waitForRunCompletion(runId, timeoutMs = 480000) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    const run = await api(`/api/runs/${runId}`);
    if (run.project_id === state.selectedProjectId) {
      upsertRunSnapshot(run);
      renderProjectState();
      if (state.selectedRunId === runId) {
        await loadArtifacts(runId);
      }
    }
    if (run.status !== "running") {
      return run;
    }
    await new Promise((resolve) => setTimeout(resolve, 1500));
  }
  return null;
}

async function handleApprovalAction(action, approvalId) {
  try {
    let backgroundStillRunning = false;
    if (action === "approve" || action === "reject") {
      await api(`/api/approval-requests/${approvalId}/resolve`, {
        method: "POST",
        body: JSON.stringify({
          decision: action === "approve" ? "approved" : "rejected",
          operator_id: state.operatorId,
          comment: action === "approve" ? "通过" : "驳回",
        }),
      });
    }
    if (action === "execute") {
      const payload = await api(`/api/approval-requests/${approvalId}/execute`, { method: "POST" });
      state.selectedRunId = payload.run.run_id;
      await selectProject(state.selectedProjectId);
      const completedRun = await waitForRunCompletion(payload.run.run_id);
      if (completedRun) {
        await loadArtifacts(payload.run.run_id);
      } else {
        backgroundStillRunning = true;
        setStatus(`续写仍在后台执行，可稍后刷新查看: ${payload.run.run_id}`, "warn");
      }
    }
    await selectProject(state.selectedProjectId);
    await loadAudit();
    if (!backgroundStillRunning) {
      setStatus("审批操作已完成");
    }
  } catch (error) {
    setStatus(String(error.message || error), "error");
  }
}

async function createProject(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const formData = new FormData(form);
  try {
    const advancedBrief = String(formData.get("default_user_brief") || "").trim();
    const defaultUserBrief = advancedBrief
      ? JSON.parse(advancedBrief)
      : {
          title: String(formData.get("brief_title") || "").trim(),
          genre: String(formData.get("brief_genre") || "").trim(),
          platform: String(formData.get("brief_platform") || "").trim(),
          hook: String(formData.get("brief_hook") || "").trim(),
          must_have: parseListField(formData.get("brief_must_have")),
          must_not_have: parseListField(formData.get("brief_must_not_have")),
        };
    const project = await api("/api/projects", {
      method: "POST",
      body: JSON.stringify({
        name: formData.get("name"),
        description: formData.get("description") || null,
        default_target_chapters: Number(formData.get("default_target_chapters") || 1),
        default_user_brief: defaultUserBrief,
      }),
    });
    form.reset();
    await loadProjects();
    await selectProject(project.project_id);
    await loadAudit();
    setStatus("项目已创建并已切换到新项目", "ready");
  } catch (error) {
    setStatus(String(error.message || error), "error");
  }
}

async function createRun() {
  if (!state.selectedProjectId) return;
  try {
    const payload = await api(`/api/projects/${state.selectedProjectId}/runs`, {
      method: "POST",
      body: JSON.stringify({ operator_id: state.operatorId }),
    });
    state.selectedRunId = payload.run_id;
    await selectProject(state.selectedProjectId);
    const completedRun = await waitForRunCompletion(payload.run_id);
    await selectProject(state.selectedProjectId);
    await loadAudit();
    if (completedRun) {
      setStatus("Run 已完成");
    } else {
      setStatus(`Run 仍在后台执行，可稍后刷新查看: ${payload.run_id}`, "warn");
    }
  } catch (error) {
    setStatus(String(error.message || error), "error");
  }
}

function saveAuth() {
  state.apiToken = el.apiToken.value.trim();
  state.operatorId = el.operatorId.value.trim() || "editor-1";
  localStorage.setItem("novelstudio_api_token", state.apiToken);
  localStorage.setItem("novelstudio_operator_id", state.operatorId);
  setStatus("连接配置已保存");
}

async function boot() {
  el.apiToken.value = state.apiToken;
  el.operatorId.value = state.operatorId;
  el.saveAuth.addEventListener("click", saveAuth);
  el.refreshProjects.addEventListener("click", () => loadProjects().catch((error) => setStatus(error.message, "error")));
  el.refreshAudit.addEventListener("click", () => loadAudit().catch((error) => setStatus(error.message, "error")));
  el.projectForm.addEventListener("submit", createProject);
  el.createRun.addEventListener("click", () => createRun());

  try {
    await loadProjects();
    await loadAudit();
  } catch (error) {
    setStatus(String(error.message || error), "error");
    renderProjects();
    renderAudit([]);
  }
}

boot();
