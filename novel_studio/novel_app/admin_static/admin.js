const state = {
  projects: [],
  selectedProjectId: null,
  selectedRunId: null,
  selectedThreadId: null,
  activeWorkspaceTab: localStorage.getItem("novelstudio_workspace_tab") || "dashboard",
  artifactRunId: null,
  artifactFingerprint: "",
  artifactItems: [],
  decisionDrafts: [],
  conversationRecoveryModes: {},
  conversationMessages: [],
  launchPlan: {
    chapterFocus: "先把悬念抛出来",
    launchNote: "",
  },
  projectSnapshot: {
    chapters: [],
    runs: [],
    approvals: [],
    conversationThreads: [],
    conversationDecisions: [],
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
  createRunQuick: document.getElementById("create-run-quick"),
  ideaCaptureForm: document.getElementById("idea-capture-form"),
  projectForm: document.getElementById("project-form"),
  projectBriefSummary: document.getElementById("project-brief-summary"),
  projectLaunchReadiness: document.getElementById("project-launch-readiness"),
  projectTitle: document.getElementById("project-title"),
  projectMeta: document.getElementById("project-meta"),
  summaryGoal: document.getElementById("summary-goal"),
  summarySystem: document.getElementById("summary-system"),
  summaryEvent: document.getElementById("summary-event"),
  summaryNext: document.getElementById("summary-next"),
  focusRunCaption: document.getElementById("focus-run-caption"),
  focusRun: document.getElementById("focus-run"),
  learningCaption: document.getElementById("learning-caption"),
  learningPanel: document.getElementById("learning-panel"),
  conversationCaption: document.getElementById("conversation-caption"),
  conversationCreateBootstrap: document.getElementById("conversation-create-bootstrap"),
  conversationCreateCharacters: document.getElementById("conversation-create-characters"),
  conversationCreateOutline: document.getElementById("conversation-create-outline"),
  conversationCreatePlanning: document.getElementById("conversation-create-planning"),
  conversationCreateRewrite: document.getElementById("conversation-create-rewrite"),
  conversationCreateRetro: document.getElementById("conversation-create-retro"),
  conversationThreadList: document.getElementById("conversation-thread-list"),
  conversationDecisionList: document.getElementById("conversation-decision-list"),
  conversationThreadCaption: document.getElementById("conversation-thread-caption"),
  conversationActionCopy: document.getElementById("conversation-action-copy"),
  conversationExecute: document.getElementById("conversation-execute"),
  conversationInterviewSummary: document.getElementById("conversation-interview-summary"),
  conversationThreadContext: document.getElementById("conversation-thread-context"),
  conversationMessageList: document.getElementById("conversation-message-list"),
  conversationForm: document.getElementById("conversation-form"),
  conversationInput: document.getElementById("conversation-input"),
  conversationSend: document.getElementById("conversation-send"),
  selectedRunLabel: document.getElementById("selected-run-label"),
  statusPill: document.getElementById("status-pill"),
  heroNote: document.getElementById("hero-note"),
  overviewStage: document.getElementById("overview-stage"),
  overviewChapter: document.getElementById("overview-chapter"),
  overviewBlocker: document.getElementById("overview-blocker"),
  overviewAction: document.getElementById("overview-action"),
  actionTitle: document.getElementById("action-title"),
  actionBody: document.getElementById("action-body"),
  workspaceTabs: Array.from(document.querySelectorAll("[data-workspace-tab]")),
  workspacePages: Array.from(document.querySelectorAll("[data-workspace-page]")),
};

const STATUS_LABELS = {
  running: "生成中",
  awaiting_approval: "等待审批",
  awaiting_execution: "等待执行",
  failed: "已失败",
  completed: "已完成",
  pending: "待处理",
  approved: "已通过",
  rejected: "已驳回",
};

const CONVERSATION_SCOPE_LABELS = {
  project_bootstrap: "立项共创",
  character_room: "人物讨论",
  outline_room: "大纲讨论",
  chapter_planning: "章卡协商",
  rewrite_intervention: "修稿会诊",
  chapter_retro: "章节复盘",
};

const CONVERSATION_SCENE_CONFIG = [
  { scope: "project_bootstrap", element: "conversationCreateBootstrap" },
  { scope: "character_room", element: "conversationCreateCharacters" },
  { scope: "outline_room", element: "conversationCreateOutline" },
  { scope: "chapter_planning", element: "conversationCreatePlanning" },
  { scope: "rewrite_intervention", element: "conversationCreateRewrite" },
  { scope: "chapter_retro", element: "conversationCreateRetro" },
];

const RECOVERY_MODE_LABELS = {
  continue: "继续当前流程",
  replan: "重做章卡",
  rewrite: "重写正文",
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

const REVIEWER_LABELS = {
  continuity: "连续性审校",
  pacing: "节奏审校",
  style: "文风审校",
  reader_sim: "读者模拟",
};

const ARTIFACT_LABELS = {
  creative_contract: "创作契约",
  story_bible: "故事设定",
  arc_plan: "卷纲规划",
  planning_context: "章卡应用证据",
  current_card: "当前章卡",
  drafting_context: "正文应用证据",
  current_draft: "当前正文草稿",
  phase_decision: "阶段决策",
  publish_package: "发布包",
  canon_state: "Canon 状态",
  feedback_summary: "反馈摘要",
  chapter_lesson: "章节经验卡",
  writer_playbook: "项目写作手册",
  issue_ledger: "问题账本",
  review_resolution_trace: "问题关闭证据",
  latest_review_reports: "审校结果",
  human_guidance: "人工指导",
  human_checkpoint: "人工检查点",
  blockers: "阻塞原因",
  event_log: "事件日志",
};

const ARTIFACT_ORDER = [
  "publish_package",
  "current_draft",
  "current_card",
  "latest_review_reports",
  "phase_decision",
  "human_checkpoint",
  "human_guidance",
  "creative_contract",
  "story_bible",
  "arc_plan",
  "planning_context",
  "canon_state",
  "drafting_context",
  "feedback_summary",
  "chapter_lesson",
  "writer_playbook",
  "issue_ledger",
  "review_resolution_trace",
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

const WORKSPACE_TAB_NOTES = {
  dashboard: "先看系统当前建议，再决定今天这本书最该推进的那一步。",
  project: "这里只处理立项和基础创作设定，不混入运行过程信息。",
  runs: "这里只看章节成果和运行记录，方便判断产出与过程是否顺畅。",
  approvals: "这里只做审批决策，先处理当前最值得裁决的一条。",
  conversation: "这里只做协作对话和结论沉淀，不被其他运行信息打断。",
  artifacts: "这里只看过程材料，适合复盘本章方向、正文、审校与经验沉淀。",
  audit: "这里只看系统记录和排障信息，日常创作时可以不打开。",
};

function setStatus(text, kind = "ready") {
  el.statusPill.textContent = text;
  el.statusPill.style.color = kind === "error" ? "#9b1c1c" : kind === "warn" ? "#8d5b00" : "#1f6b44";
  el.statusPill.style.background = kind === "error" ? "rgba(155,28,28,0.12)" : kind === "warn" ? "rgba(141,91,0,0.12)" : "rgba(31,107,68,0.12)";
}

function renderWorkspaceTab() {
  el.workspaceTabs.forEach((node) => {
    const active = node.dataset.workspaceTab === state.activeWorkspaceTab;
    node.classList.toggle("active", active);
    node.setAttribute("aria-selected", active ? "true" : "false");
  });
  el.workspacePages.forEach((node) => {
    const active = node.dataset.workspacePage === state.activeWorkspaceTab;
    node.classList.toggle("active", active);
    node.hidden = !active;
  });
  if (el.heroNote) {
    el.heroNote.textContent = WORKSPACE_TAB_NOTES[state.activeWorkspaceTab] || WORKSPACE_TAB_NOTES.dashboard;
  }
}

function setWorkspaceTab(tab) {
  state.activeWorkspaceTab = tab;
  localStorage.setItem("novelstudio_workspace_tab", tab);
  renderWorkspaceTab();
  window.scrollTo({ top: 0, behavior: "smooth" });
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

function artifactsPanel() {
  return el.artifactsList.closest(".panel");
}

function renderViewArtifactsButton(runId, artifactCount) {
  const count = Number(artifactCount || 0);
  if (count <= 0) {
    return `<button class="button ghost" data-action="view-run" data-id="${runId}" disabled>暂无工件</button>`;
  }
  return `<button class="button ghost" data-action="view-run" data-id="${runId}">查看工件（${count}）</button>`;
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

function selectedThread() {
  return (state.projectSnapshot.conversationThreads || []).find((item) => item.thread_id === state.selectedThreadId) || null;
}

function latestThreadByScope(scope) {
  return (state.projectSnapshot.conversationThreads || [])
    .filter((item) => item.scope === scope)
    .sort((left, right) => String(right.updated_at || "").localeCompare(String(left.updated_at || "")))[0] || null;
}

function conversationThreadForRun(runId, scope = "rewrite_intervention") {
  return (state.projectSnapshot.conversationThreads || []).find((item) => item.linked_run_id === runId && item.scope === scope) || null;
}

function interviewState(thread) {
  return thread?.interview_state || null;
}

function threadContext(thread) {
  return thread?.thread_context || null;
}

function humanCheckpoint(run) {
  return run?.result?.human_checkpoint || null;
}

function isRecoveryMode(value) {
  return ["continue", "replan", "rewrite"].includes(value);
}

function recoveryModeLabel(value) {
  return RECOVERY_MODE_LABELS[value] || value || "未指定";
}

function recoveryModeExecuteLabel(value) {
  if (value === "replan") return "按会诊结论重做章卡";
  if (value === "rewrite") return "按会诊结论重写正文";
  return "按会诊结论继续当前流程";
}

function recoveryModeDescription(value) {
  if (value === "replan") return "这次会先重做同一章的章卡，再按新的写前方向重写该章。";
  if (value === "rewrite") return "这次会保留当前章卡方向，但直接重写同一章正文并优先处理会诊意见。";
  return "这次会沿用当前流程结论继续执行，通常用于已经确认可直接续写下一步。";
}

function recoveryModePlan(value, context = null) {
  const chapterNo = context?.chapter_no || "?";
  if (value === "replan") {
    return {
      title: `重做第 ${chapterNo} 章章卡`,
      preserves: [
        "保留当前项目设定、卷纲、Canon 和记住的写作规则。",
        "保留这次会诊里已经确认的保留项和禁改项。",
      ],
      rewrites: [
        "重做当前章的章卡目标、节奏和钩子设计。",
        "随后基于新章卡重写同一章正文。",
      ],
      risks: [
        "当前章的结构会明显变化，之前满意的局部桥段可能被替换。",
        "耗时通常最长，但最适合章卡本身方向错了的情况。",
      ],
      immediate: [
        "先确认本章必须保留的桥段和不能动的人设边界。",
        "优先把关键修订采纳为“章卡修订”。",
      ],
    };
  }
  if (value === "rewrite") {
    return {
      title: `重写第 ${chapterNo} 章正文`,
      preserves: [
        "保留当前章卡的大方向、章节目标和主钩子。",
        "保留项目设定、Canon 和记住的长期规则。",
      ],
      rewrites: [
        "直接重写这一章正文，并优先处理会诊里确认的问题。",
        "不重做整章规划，重点是把当前章写顺、写清楚。",
      ],
      risks: [
        "如果根因其实在章卡，单纯重写正文可能再次不过。",
        "耗时中等，适合方向基本对、但落地质量不够的情况。",
      ],
      immediate: [
        "先把最关键的修订意见采纳为“修订指令”。",
        "明确哪些桥段必须保留，避免重写时把有效内容也冲掉。",
      ],
    };
  }
  return {
    title: `继续当前流程，推进到第 ${Number(chapterNo || 0) + 1 || "?"} 章`,
    preserves: [
      "保留当前章节已经通过的结果和已确认的对话结论。",
      "沿用当前章卡/正文之外的项目上下文，继续往下一步推进。",
    ],
    rewrites: [
      "不会重做当前章，重点是继续下一步或下一章。",
      "会把会诊里确认的补充规则带到后续生成里。",
    ],
    risks: [
      "如果当前章本身还有关键问题没说清，继续推进会把问题带到后面。",
      "最快，但只适合已经确认当前章可接受的情况。",
    ],
    immediate: [
      "先确认这次会诊没有要求重做当前章卡或正文。",
      "把需要延续到下一章的要求采纳为长期规则或修订指令。",
    ],
  };
}

function approvalDecisionTitle(item, recoveryMode) {
  const chapterNo = item.chapter_no || "?";
  if (recoveryMode === "replan") {
    return `第 ${chapterNo} 章方向不稳，先重做章卡`;
  }
  if (recoveryMode === "rewrite") {
    return `第 ${chapterNo} 章方向可保留，但正文需要重写`;
  }
  return `第 ${chapterNo} 章可保留，继续推进下一步`;
}

function approvalDecisionSummary(item, recoveryMode, plan) {
  const status = STATUS_LABELS[item.status] || item.status;
  if (item.status === "pending") {
    return `${status}。${item.reason} 当前更像是在决定：${recoveryModeLabel(recoveryMode)}。`;
  }
  if (item.status === "approved" && !item.executed_run_id) {
    return `${status}，尚未执行。当前将按“${recoveryModeLabel(recoveryMode)}”恢复。${plan.preserves[0]}`;
  }
  if (item.status === "approved" && item.executed_run_id) {
    return `${status}，已执行。系统已经按“${recoveryModeLabel(recoveryMode)}”进入下一条运行。`;
  }
  if (item.status === "rejected") {
    return `${status}。这次恢复路径没有被接受，建议先回到会诊线程补充说明。`;
  }
  return `${status}。${item.reason}`;
}

function approvalDecisionActions(item) {
  if (item.status === "pending") {
    return "你现在要做的是决定：接受当前恢复方案，还是先打回再讨论。";
  }
  if (item.status === "approved" && !item.executed_run_id) {
    return "你现在要做的是：确认会诊结论无误，然后执行这条恢复路径。";
  }
  if (item.status === "approved" && item.executed_run_id) {
    return "这张卡已经处理完成。下一步去看最新运行记录和过程材料。";
  }
  if (item.status === "rejected") {
    return "建议先回到会诊线程，把保留项、要改什么、不能怎么改说清楚，再决定是否重新提交。";
  }
  return "当前没有额外建议动作。";
}

function runStageSummary(run) {
  const displayStatus = runDisplayStatus(run);
  const progress = run.result?.progress || {};
  const reviewProgress = progress.review_progress || {};
  const chapterNo = chapterForRun(run);
  const currentNode = progress.current_node || "";
  const latestEvent = progress.latest_event || "run_started";
  const updatedAt = progress.updated_at ? formatTimestamp(progress.updated_at) : formatTimestamp(run.created_at);
  const staleMs = progress.updated_at ? Date.now() - new Date(progress.updated_at).getTime() : 0;
  const stale = staleMs > 180000;
  const stageGoal = progress.stage_goal || "等待下一步目标。";
  const waitingReviewers = remainingReviewers(reviewProgress).map((item) => reviewerLabel(item));

  if (run.status === "running") {
    if (reviewProgress.stage_status === "running") {
      return {
        stageTitle: "正在并行审校",
        stageLead: `第 ${chapterNo} 章已经写完，正在让 4 个审校并行复核。`,
        stageDetail: `已完成 ${reviewProgress.completed_count || 0}/${reviewProgress.total_count || 4}。${reviewerStallLabel(reviewProgress) ? `当前最慢：${reviewerStallLabel(reviewProgress)}。` : waitingReviewers.length ? `还在等：${waitingReviewers.join("、")}。` : "正在等待主编汇总。"}`,
        stageHint: stale
          ? `这条运行已经 ${formatDuration(staleMs)} 没有推进，更像是卡住了。`
          : "当前不需要重复点击，等审校返回即可。",
        stagePill: `并行审校 ${reviewProgress.completed_count || 0}/${reviewProgress.total_count || 4}`,
      };
    }
    if (["interviewer_contract", "lore_builder", "arc_planner", "chapter_planner"].includes(currentNode)) {
      return {
        stageTitle: "正在定方向",
        stageLead: `系统正在为第 ${chapterNo} 章做前期收敛，先把题材、设定、卷纲和章卡方向定稳。`,
        stageDetail: `当前环节：${nodeLabel(currentNode)}。目标：${stageGoal}`,
        stageHint: stale ? `这一步已经 ${formatDuration(staleMs)} 没进展，建议留意是否卡住。` : "这一步产出的是章卡和写前方向，不是正文。",
        stagePill: "正在定方向",
      };
    }
    if (["draft_writer", "patch_writer"].includes(currentNode)) {
      return {
        stageTitle: currentNode === "patch_writer" ? "正在重写正文" : "正在写正文",
        stageLead: `系统正在处理第 ${chapterNo} 章正文。`,
        stageDetail: `当前环节：${nodeLabel(currentNode)}。已重写 ${progress.rewrite_count ?? 0} 次。`,
        stageHint: stale ? `正文阶段已经 ${formatDuration(staleMs)} 没推进，可能需要稍后收口或重试。` : "这一段通常最耗时，尤其是真实模型模式下。",
        stagePill: currentNode === "patch_writer" ? "正在重写正文" : "正在写正文",
      };
    }
    if (currentNode === "chief_editor") {
      return {
        stageTitle: "正在做主编裁决",
        stageLead: `第 ${chapterNo} 章的审校结果已经回来，系统正在判断是通过、重做还是转人工。`,
        stageDetail: `最近事件：${eventLabel(latestEvent)}。最近更新时间：${updatedAt}。`,
        stageHint: stale ? `主编裁决已经 ${formatDuration(staleMs)} 没推进，可能需要人工关注。` : "这一步会决定是否进入人工检查点。",
        stagePill: "主编裁决中",
      };
    }
    if (["release_prepare", "canon_commit", "feedback_ingest"].includes(currentNode)) {
      return {
        stageTitle: "正在整理结果",
        stageLead: `正文已经基本完成，系统正在整理发布包、回写 Canon 和沉淀经验。`,
        stageDetail: `当前环节：${nodeLabel(currentNode)}。最近更新时间：${updatedAt}。`,
        stageHint: "这一步离最终结果很近了，通常不用再介入。",
        stagePill: "正在整理结果",
      };
    }
    return {
      stageTitle: "正在推进本章",
      stageLead: `系统正在后台处理第 ${chapterNo} 章。`,
      stageDetail: `当前环节：${nodeLabel(currentNode)}。最近更新时间：${updatedAt}。`,
      stageHint: stale ? `这条运行已经 ${formatDuration(staleMs)} 没推进，可能需要人工收口。` : "当前不需要重复点击，等系统继续推进即可。",
      stagePill: `运行中：${nodeLabel(currentNode)}`,
    };
  }

  if (displayStatus === "awaiting_approval") {
    return {
      stageTitle: "等你裁决",
      stageLead: `第 ${chapterNo} 章已经跑到人工检查点，系统暂停等你决定下一步。`,
      stageDetail: humanCheckpoint(run)?.reason || "当前需要你决定是否接受当前结果，或切换恢复路径。",
      stageHint: "先进入会诊看清保留项、重做范围和风险，再决定。",
      stagePill: "等待你裁决",
    };
  }
  if (displayStatus === "awaiting_execution") {
    return {
      stageTitle: "等你启动下一步",
      stageLead: `第 ${chapterNo} 章的处理方案已经通过，但还没真正执行。`,
      stageDetail: "当前只差你点击执行，系统就会按选定路径继续。",
      stageHint: "先确认这次要继续、重做章卡，还是重写正文，再执行。",
      stagePill: "等待执行",
    };
  }
  if (displayStatus === "approved") {
    return {
      stageTitle: "已经接力到下一步",
      stageLead: `第 ${chapterNo} 章的方案已被接受，后续运行已经启动或完成。`,
      stageDetail: "这条记录主要用于复盘，不需要重复处理。",
      stageHint: "去看最新那条运行记录更有价值。",
      stagePill: "已完成交接",
    };
  }
  if (displayStatus === "rejected") {
    return {
      stageTitle: "这章需要重新商量",
      stageLead: `第 ${chapterNo} 章当前方案没有被接受。`,
      stageDetail: run.error || "建议先回到会诊线程，把保留项和修改边界说清楚。",
      stageHint: "不要急着直接重跑，先明确为什么不接受当前方案。",
      stagePill: "需要重新商量",
    };
  }
  if (run.status === "failed") {
    return {
      stageTitle: "这章卡住了",
      stageLead: `第 ${chapterNo} 章这次没有顺利完成。`,
      stageDetail: run.error || "这条运行已经失败或被系统收口。",
      stageHint: run.result?.manual_intervention?.action === "auto_timeout"
        ? "这更像是长时间无进度，不是一直在写。建议查看工件后决定是否重试。"
        : "建议先看过程材料，再决定是否重试当前章。",
      stagePill: "需要补救",
    };
  }
  if (run.status === "completed") {
    return {
      stageTitle: "这章已经准备好",
      stageLead: `第 ${chapterNo} 章已经完成，可以先阅读结果。`,
      stageDetail: run.result?.publish_package?.blurb || "当前系统空闲，等你决定是否继续下一章。",
      stageHint: "先看发布包、正文和审校结果，再决定是否继续。",
      stagePill: "章节已完成",
    };
  }
  return {
    stageTitle: "等待下一步",
    stageLead: `第 ${chapterNo} 章当前没有明确动作。`,
    stageDetail: "请查看这条运行的详细状态。",
    stageHint: "如果没有阻塞，可以继续下一章。",
    stagePill: "等待下一步",
  };
}

function latestApprovalForThread(thread) {
  if (!thread?.linked_run_id) return null;
  return latestApprovalForRun(thread.linked_run_id, state.projectSnapshot.approvals || []);
}

function inferRecoveryModeForThread(thread) {
  if (!thread || thread.scope !== "rewrite_intervention") {
    return "continue";
  }
  const selected = state.conversationRecoveryModes[thread.thread_id];
  if (isRecoveryMode(selected)) {
    return selected;
  }
  const decisions = (state.projectSnapshot.conversationDecisions || []).filter((item) => item.thread_id === thread.thread_id);
  if (decisions.some((item) => item.decision_type === "chapter_card_patch")) {
    return "replan";
  }
  if (decisions.some((item) => item.decision_type === "human_instruction")) {
    return "rewrite";
  }
  const contextMode = threadContext(thread)?.recommended_recovery_mode;
  if (isRecoveryMode(contextMode)) {
    return contextMode;
  }
  const checkpointMode = humanCheckpoint(state.projectSnapshot.runs.find((item) => item.run_id === thread.linked_run_id))?.recommended_recovery_mode;
  if (isRecoveryMode(checkpointMode)) {
    return checkpointMode;
  }
  const approvalMode = latestApprovalForThread(thread)?.requested_action;
  if (isRecoveryMode(approvalMode)) {
    return approvalMode;
  }
  return "continue";
}

function setRecoveryModeForThread(threadId, mode) {
  if (!threadId || !isRecoveryMode(mode)) return;
  state.conversationRecoveryModes[threadId] = mode;
  renderProjectState();
}

function nodeLabel(value) {
  return NODE_LABELS[value] || value || "未记录";
}

function conversationScopeLabel(value) {
  return CONVERSATION_SCOPE_LABELS[value] || value || "创作对话";
}

function conversationThreadProgressLabel(thread) {
  const interview = interviewState(thread);
  return interview?.completion_label || null;
}

function conversationInputPlaceholder(thread) {
  if (!thread) {
    return "例如：这章我想保留主角克制的气质，但请把冲突前置，不要拖到中段。";
  }
  if (thread.scope === "project_bootstrap") {
    return "例如：我脑子里现在最清楚的是，一个被逐出山门的人，靠偷听禁地里的古老声音翻身，但我还没想清楚它更偏爽感还是悬念。";
  }
  if (thread.scope === "character_room") {
    return "例如：主角表面克制冷硬，实则极怕再失去亲近之人，所以宁可先承担风险也不会让同伴顶上。";
  }
  if (thread.scope === "outline_room") {
    return "例如：第一卷主线是主角借宗门试炼追查师门灭门真相，中段反转是发现真凶来自他最信任的一方。";
  }
  if (thread.scope === "chapter_planning") {
    return "例如：这一章我要主角主动试探敌方底牌，章末必须落在更大风险暴露。";
  }
  if (thread.scope === "rewrite_intervention") {
    return "例如：不要改掉主角克制气质，但前 800 字一定要让他先行动一次，别再铺垫过长。";
  }
  return "例如：这章通过的关键是冲突前置和钩子更明确，后面要继续保持这个节奏。";
}

function renderThreadContext(thread) {
  const context = threadContext(thread);
  if (!thread || !context) {
    el.conversationThreadContext.innerHTML = "";
    return;
  }
  if (["character_room", "outline_room"].includes(thread.scope)) {
    const inherited = context.inherited_items?.length
      ? `<ul class="interview-list">${context.inherited_items.map((item) => `<li><strong>${escapeHtml(item.label || "")}</strong>：${escapeHtml(item.summary || "")}</li>`).join("")}</ul>`
      : `<div class="meta">当前还没有明确可继承的稳定结论。</div>`;
    const missing = context.missing_items?.length
      ? `<ul class="interview-list">${context.missing_items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
      : `<div class="meta">这一步没有额外缺口，可以开始整理稳定结论。</div>`;
    el.conversationThreadContext.innerHTML = `
      <section class="interview-card">
        <div class="card-head">
          <h4>${escapeHtml(context.title || "承接说明")}</h4>
          <span class="status-chip status-approved">${thread.scope === "character_room" ? "人物线" : "大纲线"}</span>
        </div>
        <div class="meta">${escapeHtml(context.reason || "")}</div>
        <div class="interview-grid">
          <div class="interview-block">
            <strong>这一步会继承什么</strong>
            ${inherited}
          </div>
          <div class="interview-block">
            <strong>这一步还要补什么</strong>
            ${missing}
          </div>
        </div>
        <div class="interview-block">
          <strong>当前目标</strong>
          <div class="meta">${escapeHtml(context.next_goal || "")}</div>
        </div>
      </section>
    `;
    return;
  }
  if (!["chapter_planning", "rewrite_intervention"].includes(thread.scope)) {
    el.conversationThreadContext.innerHTML = "";
    return;
  }
  if (thread.scope === "rewrite_intervention") {
    const approval = latestApprovalForThread(thread);
    const selectedMode = inferRecoveryModeForThread(thread);
    const plan = recoveryModePlan(selectedMode, context);
    const mustFix = context.must_fix?.length
      ? `<ul class="interview-list">${context.must_fix.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
      : `<div class="meta">当前没有明确的必须先修项。</div>`;
    const stubborn = context.stubborn_issues?.length
      ? `<ul class="interview-list">${context.stubborn_issues.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
      : `<div class="meta">当前没有连续复发到必须人工裁决的顽固问题。</div>`;
    const suggested = context.suggested_actions?.length
      ? `<ul class="interview-list">${context.suggested_actions.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
      : `<div class="meta">当前没有额外推荐动作。</div>`;
    el.conversationThreadContext.innerHTML = `
      <section class="interview-card">
        <div class="card-head">
          <h4>人工检查点</h4>
          <span class="status-chip status-awaiting_approval">第 ${context.chapter_no || "?"} 章</span>
        </div>
        <div class="meta">${escapeHtml(context.recommendation || "")}</div>
        <div class="meta">${escapeHtml(context.checkpoint_reason || "系统已暂停，等待人工判断。")}</div>
        <div class="recovery-mode-panel">
          <div class="recovery-mode-head">
            <strong>恢复路径选择</strong>
            <div class="meta">${
              approval?.status === "approved" && !approval.executed_run_id
                ? "审批已通过，确认路径后即可执行。"
                : approval?.status === "pending"
                  ? "先处理审批，再执行你选定的恢复路径。"
                  : approval?.status === "rejected"
                    ? "这条审批已驳回。若要继续，请先调整会诊结论或重新提交。"
                    : "先在这里明确本次是继续、重做章卡，还是重写正文。"
            }</div>
          </div>
          <div class="actions recovery-mode-actions">
            ${["continue", "replan", "rewrite"]
              .map(
                (mode) => `
                  <button class="button ${selectedMode === mode ? "secondary recovery-selected" : "ghost"}" data-action="set-recovery-mode" data-mode="${mode}">
                    ${recoveryModeLabel(mode)}
                  </button>
                `
              )
              .join("")}
          </div>
          <div class="meta recovery-mode-copy">当前选择：${recoveryModeLabel(selectedMode)}。${recoveryModeDescription(selectedMode)}</div>
          <div class="interview-grid recovery-mode-grid">
            <div class="interview-block">
              <strong>${escapeHtml(plan.title)}</strong>
              <div class="meta">执行前先看清：这次到底保留什么、重做什么、风险是什么。</div>
            </div>
            <div class="interview-block">
              <strong>建议立即确认</strong>
              <ul class="interview-list">${plan.immediate.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
            </div>
            <div class="interview-block">
              <strong>这次会保留什么</strong>
              <ul class="interview-list">${plan.preserves.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
            </div>
            <div class="interview-block">
              <strong>这次会重做什么</strong>
              <ul class="interview-list">${plan.rewrites.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
            </div>
            <div class="interview-block">
              <strong>风险与代价</strong>
              <ul class="interview-list">${plan.risks.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
            </div>
          </div>
        </div>
        <div class="interview-grid">
          <div class="interview-block">
            <strong>当前为什么停在这里</strong>
            <div class="meta">${escapeHtml(context.issue_progress_summary || "当前没有更细的问题进展摘要。")}</div>
            <div class="meta">${context.approval_status ? `审批状态：${STATUS_LABELS[context.approval_status] || context.approval_status}` : "审批状态暂未记录"}</div>
          </div>
          <div class="interview-block">
            <strong>系统建议动作</strong>
            ${suggested}
          </div>
        </div>
        <div class="interview-grid">
          <div class="interview-block">
            <strong>必须先修</strong>
            ${mustFix}
          </div>
          <div class="interview-block">
            <strong>顽固问题</strong>
            ${stubborn}
          </div>
        </div>
      </section>
    `;
    el.conversationThreadContext.querySelectorAll("[data-action='set-recovery-mode']").forEach((node) => {
      node.addEventListener("click", () => setRecoveryModeForThread(thread.thread_id, node.dataset.mode));
    });
    return;
  }
  const mustInclude = context.must_include?.length
    ? `<ul class="interview-list">${context.must_include.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
    : `<div class="meta">当前章卡还没有明确的“必须兑现”。</div>`;
  const mustNotChange = context.must_not_change?.length
    ? `<ul class="interview-list">${context.must_not_change.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
    : `<div class="meta">当前没有记录硬性不可改动项。</div>`;
  const pendingIssues = context.pending_issues?.length
    ? `<ul class="interview-list">${context.pending_issues.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
    : `<div class="meta">当前没有明显遗留问题阻塞本章。</div>`;
  const guardrails = context.guardrails?.length
    ? `<ul class="interview-list">${context.guardrails.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
    : `<div class="meta">当前没有额外章卡防线。</div>`;
  const patches = context.patch_highlights?.length
    ? `<ul class="interview-list">${context.patch_highlights.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
    : `<div class="meta">你还没有采纳章卡修订。先把想改的点说清楚，再采纳为章卡修订。</div>`;
  el.conversationThreadContext.innerHTML = `
    <section class="interview-card">
      <div class="card-head">
        <h4>写前确认卡</h4>
        <span class="status-chip status-approved">第 ${context.chapter_no || "?"} 章</span>
      </div>
      <div class="meta">${escapeHtml(context.recommendation || "")}</div>
      <div class="interview-grid">
        <div class="interview-block">
          <strong>本章默认目标</strong>
          <div class="meta">${escapeHtml(context.purpose || "当前还没有形成明确章卡目标。")}</div>
          <div class="meta">${context.pov ? `默认视角：${escapeHtml(context.pov)}` : "默认视角暂未记录"}</div>
        </div>
        <div class="interview-block">
          <strong>本章修订进度</strong>
          <div class="meta">已采纳章卡修订 ${context.patch_count || 0} 条</div>
          ${patches}
        </div>
      </div>
      <div class="interview-grid">
        <div class="interview-block">
          <strong>本章必须兑现</strong>
          ${mustInclude}
        </div>
        <div class="interview-block">
          <strong>本章不可破坏</strong>
          ${mustNotChange}
        </div>
      </div>
      <div class="interview-grid">
        <div class="interview-block">
          <strong>需提前规避的问题</strong>
          ${pendingIssues}
        </div>
        <div class="interview-block">
          <strong>章卡层已前置防线</strong>
          ${guardrails}
        </div>
      </div>
    </section>
  `;
}

function conversationRoleLabel(role, messageType) {
  if (role === "user") return "你";
  if (messageType === "assistant_diagnosis") return "系统诊断";
  if (messageType === "assistant_question") return "系统追问";
  if (messageType === "assistant_proposal") return "系统建议";
  if (role === "assistant") return "系统";
  return "系统记录";
}

function conversationDecisionLabel(value) {
  if (value === "human_instruction") return "修订指令";
  if (value === "writer_playbook_rule") return "写作规则";
  if (value === "character_note") return "人物设定";
  if (value === "outline_constraint") return "卷纲约束";
  if (value === "chapter_card_patch") return "章卡修订";
  return value || "已采纳结论";
}

function editableDecisionContent(item) {
  return item.payload.comment || item.payload.rule || item.payload.note || item.payload.constraint || item.payload.instruction || item.payload.content || "";
}

function conversationDecisionGroup(value) {
  if (value === "character_note") return "characters";
  if (value === "outline_constraint") return "outline";
  if (value === "writer_playbook_rule") return "long_term";
  return "chapter";
}

function conversationDecisionGroupLabel(group) {
  if (group === "characters") return "人物";
  if (group === "outline") return "大纲";
  if (group === "long_term") return "长期规则";
  return "本章修订";
}

function draftDecisionLabel(decisionType) {
  return conversationDecisionLabel(decisionType);
}

function compactDecisionText(value, maxLength = 44) {
  const text = String(value || "").trim().replace(/\s+/g, " ");
  if (!text) return "";
  return text.length > maxLength ? `${text.slice(0, maxLength)}...` : text;
}

function summarizeDecisionGroup(groupItems, groupDrafts) {
  const highlights = [
    ...groupDrafts.map((item) => ({ text: item.content, draft: true })),
    ...groupItems.map((item) => ({ text: editableDecisionContent(item), draft: false })),
  ]
    .map((item) => ({
      ...item,
      text: compactDecisionText(item.text),
    }))
    .filter((item) => item.text)
    .slice(0, 3);
  return {
    adoptedCount: groupItems.length,
    draftCount: groupDrafts.length,
    highlights,
  };
}

function summarizeAppliedGuidanceGroup(run, groupKey) {
  const guidance = conversationGuidance(run);
  const adopted = guidance?.adopted_decisions || [];
  const matches = adopted
    .filter((item) => conversationDecisionGroup(item.decision_type) === groupKey)
    .map((item) => compactDecisionText(item.summary))
    .filter(Boolean)
    .slice(0, 3);
  return {
    appliedCount: matches.length,
    highlights: matches,
  };
}

function interviewDraftActions(thread, section) {
  if (!thread || !section) return [];
  if (thread.scope === "project_bootstrap") {
    if (section.label === "最想保住的吸引力" || section.label === "不能写歪的边界") {
      return [{ label: "采纳为长期规则", decisionType: "writer_playbook_rule" }];
    }
    if (section.label === "主角行动方式") {
      return [{ label: "采纳为人物设定", decisionType: "character_note" }];
    }
    if (section.label === "故事推进方式") {
      return [{ label: "采纳为卷纲约束", decisionType: "outline_constraint" }];
    }
    return [
      { label: "采纳为人物设定", decisionType: "character_note" },
      { label: "采纳为卷纲约束", decisionType: "outline_constraint" },
      { label: "采纳为长期规则", decisionType: "writer_playbook_rule" },
    ];
  }
  if (thread.scope === "character_room") {
    return [{ label: "采纳为人物设定", decisionType: "character_note" }];
  }
  if (thread.scope === "outline_room") {
    return [{ label: "采纳为卷纲约束", decisionType: "outline_constraint" }];
  }
  return [{ label: "采纳为写作规则", decisionType: "writer_playbook_rule" }];
}

async function openOrCreateConversationScope(scope) {
  if (!state.selectedProjectId) return;
  const existing = (state.projectSnapshot.conversationThreads || []).find((item) => item.scope === scope && item.status === "open");
  if (existing) {
    state.selectedThreadId = existing.thread_id;
    await loadConversationMessages(existing.thread_id, { activateTab: true });
    setStatus(`已进入${conversationScopeLabel(scope)}线程`, "ready");
    return;
  }
  await createConversationThread(scope);
}

function renderInterviewSummary(thread) {
  const interview = interviewState(thread);
  if (!thread || !interview) {
    el.conversationInterviewSummary.innerHTML = "";
    return;
  }
  const confirmed = interview.confirmed_topics?.length
    ? `<ul class="interview-list">${interview.confirmed_topics.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
    : `<div class="meta">还没有稳定确认项，先从当前下一问开始回答。</div>`;
  const unresolved = interview.unresolved_topics?.length
    ? `<ul class="interview-list">${interview.unresolved_topics.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
    : `<div class="meta">当前关键问题已基本问清，可以开始采纳并执行。</div>`;
  const basis = interview.basis?.length
    ? `<div class="meta">${interview.basis.map((item) => escapeHtml(item)).join(" / ")}</div>`
    : `<div class="meta">当前还没有明确的项目基础信息。</div>`;
  const adopted = interview.adopted_highlights?.length
    ? `<div class="meta">${interview.adopted_highlights.map((item) => escapeHtml(compactDecisionText(item, 36))).join(" / ")}</div>`
    : `<div class="meta">当前线程还没有采纳结论。</div>`;
  const skipped = interview.skipped_topics?.length
    ? `<div class="meta">已跳过：${interview.skipped_topics.map((item) => escapeHtml(item)).join("、")}</div>`
    : "";
  const optionButtons = interview.next_options?.length
    ? `
      <div class="interview-options">
        ${interview.next_options
          .map((item, index) => `<button class="button ghost interview-option" type="button" data-interview-option="${index}">${escapeHtml(item)}</button>`)
          .join("")}
        <button class="button ghost interview-option ghost" type="button" data-interview-helper="skip">先跳过</button>
        <button class="button ghost interview-option ghost" type="button" data-interview-helper="rephrase">换个问法</button>
        <button class="button ghost interview-option ghost" type="button" data-interview-helper="more-options">给我更多选项</button>
        <button class="button ghost interview-option ghost" type="button" data-interview-helper="unsure">我还不确定</button>
      </div>
    `
    : "";
  const currentDraft = interview.current_draft
    ? `
      <section class="interview-draft">
        <div class="card-head">
          <h4>${escapeHtml(interview.current_draft.title || "当前理解草案")}</h4>
          <span class="status-chip status-approved">可确认</span>
        </div>
        <div class="meta">${escapeHtml(interview.current_draft.lead || "")}</div>
        <div class="stack compact">
          ${(interview.current_draft.sections || [])
            .map((item, index) => {
              const actions = interviewDraftActions(thread, item);
              return `
                <div class="interview-block">
                  <strong>${escapeHtml(item.label || "")}</strong>
                  <div class="meta">${escapeHtml(item.summary || "")}</div>
                  ${
                    actions.length
                      ? `<div class="actions">${actions
                          .map(
                            (action) =>
                              `<button class="button ghost" type="button" data-draft-adopt="${index}" data-decision-type="${action.decisionType}">${action.label}</button>`
                          )
                          .join("")}</div>`
                      : ""
                  }
                </div>
              `;
            })
            .join("")}
        </div>
        <div class="meta">${escapeHtml(interview.current_draft.recommendation || "")}</div>
        <div class="actions">
          <button class="button ghost" type="button" data-draft-confirm="true">确认这版理解</button>
        </div>
      </section>
    `
    : "";
  const stageConfirmation = interview.stage_confirmation
    ? `
      <section class="interview-stage-card">
        <div class="card-head">
          <h4>阶段确认页</h4>
          <span class="status-chip status-approved">先确认，再分流</span>
        </div>
        <div class="interview-grid">
          <div class="interview-block">
            <strong>已确认</strong>
            ${
              interview.stage_confirmation.confirmed_items?.length
                ? `<ul class="interview-list">${interview.stage_confirmation.confirmed_items
                    .map((item) => `<li><strong>${escapeHtml(item.label || "")}</strong>：${escapeHtml(item.summary || "")}</li>`)
                    .join("")}</ul>`
                : `<div class="meta">当前还没有足够明确的已确认内容。</div>`
            }
          </div>
          <div class="interview-block">
            <strong>暂定表达</strong>
            ${
              interview.stage_confirmation.provisional_items?.length
                ? `<ul class="interview-list">${interview.stage_confirmation.provisional_items
                    .map((item) => `<li><strong>${escapeHtml(item.label || "")}</strong>：${escapeHtml(item.summary || "")}</li>`)
                    .join("")}</ul>`
                : `<div class="meta">系统还没有整理出暂定表达。</div>`
            }
          </div>
        </div>
        <div class="interview-grid">
          <div class="interview-block">
            <strong>未决问题</strong>
            ${
              interview.stage_confirmation.open_questions?.length
                ? `<ul class="interview-list">${interview.stage_confirmation.open_questions.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
                : `<div class="meta">当前关键问题已基本问清。</div>`
            }
          </div>
          <div class="interview-block">
            <strong>建议下一步</strong>
            ${
              interview.stage_confirmation.next_steps?.length
                ? `<div class="stack compact">${interview.stage_confirmation.next_steps
                    .map(
                      (step) => `
                        <div class="interview-next-step">
                          <div class="meta"><strong>${escapeHtml(step.label || "")}</strong>${step.recommended ? " · 推荐" : ""}</div>
                          <div class="meta">${escapeHtml(step.reason || "")}</div>
                          <div class="actions">
                            <button class="button ghost" type="button" data-stage-open-scope="${step.scope}">${escapeHtml(step.label || "进入下一步")}</button>
                          </div>
                        </div>
                      `
                    )
                    .join("")}</div>`
                : `<div class="meta">当前阶段还没有额外分流建议。</div>`
            }
          </div>
        </div>
        ${
          interview.stage_confirmation.decision_split_preview
            ? `
              <div class="interview-block">
                <strong>可直接拆出的第一批结论</strong>
                <div class="meta">
                  人物设定 ${interview.stage_confirmation.decision_split_preview.counts?.character_note || 0} 条 /
                  卷纲约束 ${interview.stage_confirmation.decision_split_preview.counts?.outline_constraint || 0} 条 /
                  长期规则 ${interview.stage_confirmation.decision_split_preview.counts?.writer_playbook_rule || 0} 条
                </div>
                <ul class="interview-list">
                  ${(interview.stage_confirmation.decision_split_preview.items || [])
                    .map(
                      (item) =>
                        `<li><strong>${escapeHtml(item.label || "")}</strong> → ${escapeHtml(conversationDecisionLabel(item.decision_type || ""))}：${escapeHtml(item.content || "")}</li>`
                    )
                    .join("")}
                </ul>
                <div class="actions">
                  <button class="button secondary" type="button" data-stage-split-summary="${thread.thread_id}">拆成第一批结论</button>
                </div>
              </div>
            `
            : ""
        }
        ${
          interview.stage_confirmation.stage_summary
            ? `
              <section class="interview-draft summary">
                <div class="card-head">
                  <h4>${escapeHtml(interview.stage_confirmation.stage_summary.title || "阶段摘要")}</h4>
                  <span class="status-chip status-approved">阶段摘要</span>
                </div>
                <ul class="interview-list">
                  ${(interview.stage_confirmation.stage_summary.items || [])
                    .map((item) => `<li><strong>${escapeHtml(item.label || "")}</strong>：${escapeHtml(item.summary || "")}</li>`)
                    .join("")}
                </ul>
                <div class="meta">${escapeHtml(interview.stage_confirmation.stage_summary.readiness || "")}</div>
                <div class="actions">
                  <button class="button secondary" type="button" data-apply-stage-summary="${thread.thread_id}">写回项目设定</button>
                </div>
              </section>
            `
            : ""
        }
      </section>
  `
    : "";
  el.conversationInterviewSummary.innerHTML = `
    <section class="interview-card">
      <div class="card-head">
        <h4>共创采访进度</h4>
        <span class="status-chip status-approved">已确认 ${interview.completion_label}</span>
      </div>
      <div class="meta">${escapeHtml(interview.goal || "")}</div>
      <div class="meta">${escapeHtml(interview.reflection_summary || "")}</div>
      ${basis}
      <div class="interview-grid">
        <div class="interview-block">
          <strong>已确认事项</strong>
          ${confirmed}
          ${skipped}
        </div>
        <div class="interview-block">
          <strong>未决问题</strong>
          ${unresolved}
        </div>
      </div>
      <div class="interview-grid">
        <div class="interview-block">
          <strong>系统下一问</strong>
          <div class="meta">${escapeHtml(interview.next_prompt || "继续补充你认为最关键的信息。")}</div>
          ${optionButtons}
        </div>
        <div class="interview-block">
          <strong>当前已采纳</strong>
          <div class="meta">已采纳 ${interview.adopted_count || 0} 条</div>
          ${adopted}
        </div>
      </div>
      ${stageConfirmation}
      ${currentDraft}
    </section>
  `;
  el.conversationInterviewSummary.querySelectorAll("[data-interview-option]").forEach((node) => {
    node.addEventListener("click", () => {
      const choice = interview.next_options?.[Number(node.dataset.interviewOption)] || "";
      if (!choice) return;
      el.conversationInput.value = choice;
      el.conversationInput.focus();
      setStatus("已把候选回答带入输入框，你可以直接发送或再补一句。", "ready");
    });
  });
  el.conversationInterviewSummary.querySelectorAll("[data-interview-helper]").forEach((node) => {
    node.addEventListener("click", async () => {
      const helper =
        node.dataset.interviewHelper === "skip"
          ? "先跳过这个问题，继续问下一个。"
          : node.dataset.interviewHelper === "rephrase"
            ? "换个问法。"
            : node.dataset.interviewHelper === "more-options"
              ? "给我更多选项。"
              : "我还不确定，先给我几个更具体的方向。";
      try {
        await submitConversationMessage(helper);
      } catch (error) {
        setStatus(String(error.message || error), "error");
      }
    });
  });
  el.conversationInterviewSummary.querySelectorAll("[data-draft-confirm]").forEach((node) => {
    node.addEventListener("click", async () => {
      try {
        await submitConversationMessage("这版理解基本对，请继续细化。");
      } catch (error) {
        setStatus(String(error.message || error), "error");
      }
    });
  });
  el.conversationInterviewSummary.querySelectorAll("[data-draft-adopt]").forEach((node) => {
    node.addEventListener("click", async () => {
      const index = Number(node.dataset.draftAdopt);
      const decisionType = node.dataset.decisionType;
      const section = interview.current_draft?.sections?.[index];
      if (!section || !decisionType || !thread) return;
      try {
        await createConversationDecisionFromDraft({
          threadId: thread.thread_id,
          decisionType,
          content: section.summary,
          sourceLabel: `${interview.current_draft.title || "当前理解草案"} · ${section.label}`,
        });
      } catch (error) {
        setStatus(String(error.message || error), "error");
      }
    });
  });
  el.conversationInterviewSummary.querySelectorAll("[data-stage-open-scope]").forEach((node) => {
    node.addEventListener("click", async () => {
      try {
        await openOrCreateConversationScope(node.dataset.stageOpenScope);
      } catch (error) {
        setStatus(String(error.message || error), "error");
      }
    });
  });
  el.conversationInterviewSummary.querySelectorAll("[data-stage-split-summary]").forEach((node) => {
    node.addEventListener("click", async () => {
      try {
        await splitStageSummary(node.dataset.stageSplitSummary);
      } catch (error) {
        setStatus(String(error.message || error), "error");
      }
    });
  });
  el.conversationInterviewSummary.querySelectorAll("[data-apply-stage-summary]").forEach((node) => {
    node.addEventListener("click", async () => {
      try {
        await applyStageSummary(node.dataset.applyStageSummary);
      } catch (error) {
        setStatus(String(error.message || error), "error");
      }
    });
  });
}

function projectSummarySource(project) {
  if (!project) return null;
  const applied = project.default_user_brief?.project_summary;
  if (applied) {
    return {
      summary: applied,
      status: "applied",
      threadId: applied.source_thread_id || null,
    };
  }
  const bootstrapThread = latestThreadByScope("project_bootstrap");
  const draftSummary = bootstrapThread?.interview_state?.stage_confirmation?.project_summary;
  if (draftSummary) {
    return {
      summary: draftSummary,
      status: "draft",
      threadId: bootstrapThread.thread_id,
    };
  }
  return null;
}

function scopedSummarySource(project, scope) {
  if (!project) return null;
  const key = scope === "character_room" ? "character_summary" : scope === "outline_room" ? "outline_summary" : null;
  if (!key) return null;
  const applied = project.default_user_brief?.[key];
  if (applied) {
    return {
      summary: applied,
      status: "applied",
      threadId: applied.source_thread_id || null,
    };
  }
  const thread = latestThreadByScope(scope);
  const draftSummary = thread?.interview_state?.stage_confirmation?.stage_summary;
  if (draftSummary) {
    return {
      summary: draftSummary,
      status: "draft",
      threadId: thread.thread_id,
    };
  }
  return null;
}

function openingReadiness(project) {
  if (!project) {
    return {
      ready: false,
      completed: 0,
      total: 3,
      missingScopes: ["project_bootstrap", "character_room", "outline_room"],
      items: [],
    };
  }
  const projectStage = projectSummarySource(project);
  const characterStage = scopedSummarySource(project, "character_room");
  const outlineStage = scopedSummarySource(project, "outline_room");
  const items = [
    {
      scope: "project_bootstrap",
      label: "项目方向",
      done: projectStage?.status === "applied",
      summary: projectStage?.summary?.readiness || "先把立项共创整理成第一版项目设定摘要。",
    },
    {
      scope: "character_room",
      label: "人物设定",
      done: characterStage?.status === "applied",
      summary: characterStage?.summary?.readiness || "先把主角气质、欲望和边界收紧成人物设定摘要。",
    },
    {
      scope: "outline_room",
      label: "第一卷方向",
      done: outlineStage?.status === "applied",
      summary: outlineStage?.summary?.readiness || "先把第一卷推进方式、反转和卷末兑现整理成方向摘要。",
    },
  ];
  const completed = items.filter((item) => item.done).length;
  return {
    ready: completed === items.length,
    completed,
    total: items.length,
    missingScopes: items.filter((item) => !item.done).map((item) => item.scope),
    items,
  };
}

function launchAppliedSummarySources(project) {
  return [
    {
      label: "项目方向",
      source: projectSummarySource(project),
    },
    {
      label: "人物设定",
      source: scopedSummarySource(project, "character_room"),
    },
    {
      label: "第一卷方向",
      source: scopedSummarySource(project, "outline_room"),
    },
  ].filter((item) => item.source?.summary);
}

function launchInheritedItems(project) {
  return launchAppliedSummarySources(project)
    .flatMap((item) =>
      (item.source.summary.items || []).slice(0, 2).map((entry) => ({
        scopeLabel: item.label,
        label: entry.label || item.label,
        summary: entry.summary || "",
      }))
    )
    .filter((item) => item.summary)
    .slice(0, 6);
}

function launchOpenQuestions(project) {
  return launchAppliedSummarySources(project)
    .flatMap((item) =>
      (item.source.summary.open_questions || []).map((question) => ({
        scopeLabel: item.label,
        question,
      }))
    )
    .filter((item) => item.question)
    .slice(0, 6);
}

function launchScopedItems(project, key) {
  return launchAppliedSummarySources(project)
    .flatMap((item) =>
      (item.source.summary[key] || []).map((entry) => ({
        scopeLabel: item.label,
        label: entry.label || item.label,
        summary: entry.summary || "",
      }))
    )
    .filter((item) => item.summary)
    .slice(0, 6);
}

function nextPlannedChapter(project) {
  const latest = latestChapterNo(state.projectSnapshot.chapters || []);
  if (latest > 0) return latest + 1;
  return Number(project?.default_target_chapters || 1) > 0 ? 1 : 1;
}

function renderProjectLaunchReadiness(project) {
  if (!el.projectLaunchReadiness) return;
  const readiness = openingReadiness(project);
  if (!project) {
    el.projectLaunchReadiness.innerHTML = `
      <div class="panel-head">
        <div>
          <h3>开书确认页</h3>
          <div class="muted">先选中项目，系统再告诉你是否已经具备开始首章的条件。</div>
        </div>
      </div>
    `;
    return;
  }
  const inheritedItems = launchInheritedItems(project);
  const confirmedItems = launchScopedItems(project, "confirmed_items");
  const provisionalItems = launchScopedItems(project, "provisional_items");
  const openQuestions = launchOpenQuestions(project);
  const plannedChapter = nextPlannedChapter(project);
  const focusOptions = [
    "先把悬念抛出来",
    "先把主角立住",
    "先把世界规则和冲突立住",
    "先验证文风和人物关系",
  ];
  const items = readiness.items
    .map(
      (item) => `
        <div class="check-card ${item.done ? "ready" : "pending"}">
          <div class="card-head">
            <h4>${item.label}</h4>
            <span class="status-chip ${item.done ? "status-approved" : "status-pending"}">${item.done ? "已确认" : "待补齐"}</span>
          </div>
          <div class="meta">${escapeHtml(item.summary || "")}</div>
          ${
            item.done
              ? ""
              : `<div class="actions"><button class="button ghost" type="button" data-launch-open-scope="${item.scope}">去补这一步</button></div>`
          }
        </div>
      `
    )
    .join("");
  const hardConstraintHtml = confirmedItems.length
    ? `<ul class="interview-list">${confirmedItems
        .map(
          (item) =>
            `<li><strong>${escapeHtml(item.scopeLabel)} · ${escapeHtml(item.label || "")}</strong>：${escapeHtml(item.summary || "")}</li>`
        )
        .join("")}</ul>`
    : inheritedItems.length
      ? `<ul class="interview-list">${inheritedItems
          .map(
            (item) =>
              `<li><strong>${escapeHtml(item.scopeLabel)} · ${escapeHtml(item.label || "")}</strong>：${escapeHtml(item.summary || "")}</li>`
          )
          .join("")}</ul>`
      : `<div class="launch-note">正式首章的硬约束，会在三层摘要写回后显示在这里。</div>`;
  const provisionalHtml = provisionalItems.length
    ? `<ul class="interview-list">${provisionalItems
        .map(
          (item) =>
            `<li><strong>${escapeHtml(item.scopeLabel)} · ${escapeHtml(item.label || "")}</strong>：${escapeHtml(item.summary || "")}</li>`
        )
        .join("")}</ul>`
    : `<div class="launch-note">${readiness.ready ? "当前没有明显的暂定方向残留，首章可以按更稳定的项目理解起步。" : "等阶段摘要再收紧一些，这里会显示“先这样理解、后面再细化”的暂定方向。"} </div>`;
  const unresolvedHtml = openQuestions.length
    ? `<ul class="interview-list">${openQuestions
        .map((item) => `<li><strong>${escapeHtml(item.scopeLabel)}</strong>：${escapeHtml(item.question || "")}</li>`)
        .join("")}</ul>
       <div class="launch-note">这些问题不会阻止你开书，但会继续保留到后续人物讨论、章卡讨论和正文修订里慢慢收紧。</div>`
    : `<div class="launch-note">${readiness.ready ? "当前三层摘要里没有明显的未决问题，可以直接把注意力放到首章。": "等三层摘要再补齐一些，系统才会更清楚哪些问题可以留到后面慢慢解决。"} </div>`;
  const readinessReasons = readiness.ready
    ? [
        `项目方向、人物设定、第一卷方向都已经写回，首章不会再从一团模糊想法开始。`,
        `首章将优先遵守 ${Math.max(confirmedItems.length, inheritedItems.length)} 条硬约束，再带着暂定方向继续细化。`,
        openQuestions.length
          ? `仍有 ${openQuestions.length} 个未决问题会被保留，但它们已经被收拢到可继续细化的范围内。`
          : `当前没有明显未决问题，已经具备正式进入首章的条件。`,
      ]
    : [
        `现在只完成了 ${readiness.completed}/${readiness.total} 项，正式首章还缺稳定的开书地基。`,
        `优先补齐 ${readiness.items
          .filter((item) => !item.done)
          .map((item) => item.label)
          .join("、")}，后续章卡和正文会明显更稳。`,
        `如果你只是想先试试感觉，可以继续用“快速试写”，但它不等于正式开书。`,
      ];
  const readinessWhyHtml = `<ul class="interview-list">${readinessReasons
    .map((item) => `<li>${escapeHtml(item)}</li>`)
    .join("")}</ul>
    <div class="launch-note">${
      readiness.ready
        ? "正式模式会先按完整项目摘要生成章卡，再进入正文、审校和必要的修订；它不是低成本试跑。"
        : "在你只想快速摸方向时，可以先用“快速试写”；正式模式建议在三层摘要补齐后再启用。"
    }</div>`;
  const launchCopy = readiness.ready
    ? "三层开书信息已经齐了。现在可以直接开始正式首章创作。"
    : `当前已完成 ${readiness.completed}/${readiness.total} 项。建议先补齐缺口，再开始正式首章；如果只是想低成本试方向，可以继续用“快速试写”。`;
  el.projectLaunchReadiness.innerHTML = `
    <div class="panel-head">
      <div>
        <h3>开书确认页</h3>
        <div class="muted">${launchCopy}</div>
      </div>
      <div class="actions">
        <button class="button ${readiness.ready ? "primary" : "ghost"}" type="button" data-launch-start="true" ${readiness.ready ? "" : "disabled"}>以正式模式开始首章</button>
        <button class="button ghost" type="button" data-launch-quick="true">只做快速试写</button>
      </div>
    </div>
    <div class="launch-checklist">${items}</div>
    <div class="launch-detail-grid">
      <div class="summary-card accent">
        <div class="summary-label">首章硬约束</div>
        <div class="summary-value">正式模式下，章卡和正文会优先遵守这些已经确认的约束。</div>
        ${hardConstraintHtml}
      </div>
      <div class="summary-card">
        <div class="summary-label">暂定方向与未决问题</div>
        <div class="summary-value">这些内容会先按当前理解进入首章，后续仍允许继续细化。</div>
        ${provisionalHtml}
        ${unresolvedHtml}
      </div>
      <div class="summary-card">
        <div class="summary-label">正式模式会怎么跑</div>
        <div class="summary-value">这是系统判断“现在适不适合正式开书”以及正式模式默认做法的说明。</div>
        ${readinessWhyHtml}
      </div>
      <div class="summary-card accent">
        <div class="summary-label">首章启动单</div>
        <div class="summary-value">本次将启动第 ${plannedChapter} 章。正式模式会先生成章卡，再写正文，再进入审校与必要修订。</div>
        <div class="launch-note">你可以在真正开始前，补一句“这一章最想优先兑现什么”。这会作为本次首章的额外启动要求带进系统。</div>
        <div class="launch-focus-options">
          ${focusOptions
            .map(
              (item) =>
                `<button class="launch-focus-chip ${state.launchPlan.chapterFocus === item ? "active" : ""}" type="button" data-launch-focus="${escapeHtml(item)}">${escapeHtml(item)}</button>`
            )
            .join("")}
        </div>
        <textarea class="launch-textarea" data-launch-note placeholder="可选：补一句这次首章最想先做到什么，例如“先把主角被动困局写扎实，但不要急着把底牌交代完”。">${escapeHtml(
          state.launchPlan.launchNote || ""
        )}</textarea>
      </div>
    </div>
  `;
  el.projectLaunchReadiness.querySelectorAll("[data-launch-open-scope]").forEach((node) => {
    node.addEventListener("click", async () => {
      try {
        await openOrCreateConversationScope(node.dataset.launchOpenScope);
      } catch (error) {
        setStatus(String(error.message || error), "error");
      }
    });
  });
  el.projectLaunchReadiness.querySelectorAll("[data-launch-start]").forEach((node) => {
    node.addEventListener("click", async () => {
      try {
        setWorkspaceTab("dashboard");
        await createRun({
          quickMode: false,
          chapterFocus: state.launchPlan.chapterFocus,
          launchNote: state.launchPlan.launchNote,
        });
      } catch (error) {
        setStatus(String(error.message || error), "error");
      }
    });
  });
  el.projectLaunchReadiness.querySelectorAll("[data-launch-quick]").forEach((node) => {
    node.addEventListener("click", async () => {
      try {
        setWorkspaceTab("dashboard");
        await createRun({ quickMode: true });
      } catch (error) {
        setStatus(String(error.message || error), "error");
      }
    });
  });
  el.projectLaunchReadiness.querySelectorAll("[data-launch-focus]").forEach((node) => {
    node.addEventListener("click", () => {
      state.launchPlan.chapterFocus = node.dataset.launchFocus || state.launchPlan.chapterFocus;
      renderProjectLaunchReadiness(project);
    });
  });
  el.projectLaunchReadiness.querySelectorAll("[data-launch-note]").forEach((node) => {
    node.addEventListener("input", () => {
      state.launchPlan.launchNote = node.value;
    });
  });
}

function renderProjectBriefSummary(project) {
  if (!el.projectBriefSummary) return;
  if (!project) {
    el.projectBriefSummary.innerHTML = `
      <div class="panel-head">
        <div>
          <h3>当前项目摘要</h3>
          <div class="muted">先选择一个项目，或从下方开始新的立项共创。</div>
        </div>
      </div>
    `;
    return;
  }
  const summarySource = projectSummarySource(project);
  const characterSource = scopedSummarySource(project, "character_room");
  const outlineSource = scopedSummarySource(project, "outline_room");
  const intentProfile = project.default_user_brief?.intent_profile || {};
  if (!summarySource) {
    const renderScopeSummary = (label, source, openScope) => {
      if (!source) {
        return `
          <div class="summary-card">
            <div class="summary-label">${label}</div>
            <div class="meta">这条线还没有形成阶段摘要。</div>
            <div class="actions">
              <button class="button ghost" type="button" data-project-summary-open="${openScope}">进入${conversationScopeLabel(openScope)}</button>
            </div>
          </div>
        `;
      }
      return `
        <div class="summary-card">
          <div class="summary-label">${label}</div>
          <ul class="interview-list">
            ${(source.summary.items || [])
              .slice(0, 3)
              .map((item) => `<li><strong>${escapeHtml(item.label || "")}</strong>：${escapeHtml(item.summary || "")}</li>`)
              .join("")}
          </ul>
          <div class="meta">${escapeHtml(source.summary.readiness || "")}</div>
          <div class="actions">
            ${
              source.status === "draft"
                ? `<button class="button secondary" type="button" data-apply-stage-summary="${escapeHtml(source.threadId || "")}">写回项目设定</button>`
                : ""
            }
            <button class="button ghost" type="button" data-project-summary-open="${openScope}">进入${conversationScopeLabel(openScope)}</button>
          </div>
        </div>
      `;
    };
    el.projectBriefSummary.innerHTML = `
      <div class="panel-head">
        <div>
          <h3>当前项目摘要</h3>
          <div class="muted">这个项目还没有整理出第一版摘要。建议先进入立项共创，把模糊想法问清。</div>
        </div>
        <div class="actions">
          <button class="button ghost" type="button" data-project-summary-open="project_bootstrap">继续立项共创</button>
        </div>
      </div>
    `;
  } else {
    const items = (summarySource.summary.items || [])
      .map((item) => `<li><strong>${escapeHtml(item.label || "")}</strong>：${escapeHtml(item.summary || "")}</li>`)
      .join("");
    const intentList = Object.entries(intentProfile)
      .filter(([, value]) => String(value || "").trim())
      .slice(0, 4)
      .map(([key, value]) => `<li><strong>${escapeHtml(key)}</strong>：${escapeHtml(String(value))}</li>`)
      .join("");
    el.projectBriefSummary.innerHTML = `
      <div class="panel-head">
        <div>
          <h3>当前项目摘要</h3>
          <div class="muted">${summarySource.status === "applied" ? "这版摘要已经写回项目设定，后续会持续作为默认项目稿使用。" : "这是一版待确认的阶段摘要。确认后可直接写回项目设定。"}
          </div>
        </div>
        <div class="actions">
          ${
            summarySource.status === "draft"
              ? `<button class="button secondary" type="button" data-project-summary-apply="${escapeHtml(summarySource.threadId || "")}">写回项目设定</button>`
              : ""
          }
          <button class="button ghost" type="button" data-project-summary-open="project_bootstrap">继续立项共创</button>
          <button class="button ghost" type="button" data-project-summary-open="character_room">进入人物讨论</button>
          <button class="button ghost" type="button" data-project-summary-open="outline_room">进入大纲讨论</button>
        </div>
      </div>
      <div class="project-brief-summary">
        <div class="summary-card">
          <div class="summary-label">第一版项目设定摘要</div>
          <ul class="interview-list">${items || "<li>当前还没有摘要内容。</li>"}</ul>
          <div class="meta">${escapeHtml(summarySource.summary.readiness || "")}</div>
        </div>
        <div class="summary-card">
          <div class="summary-label">当前意图画像</div>
          ${
            intentList
              ? `<ul class="interview-list">${intentList}</ul>`
              : `<div class="meta">意图画像会在立项共创确认后写回这里。</div>`
          }
        </div>
        ${renderScopeSummary("人物设定摘要", characterSource, "character_room")}
        ${renderScopeSummary("第一卷方向摘要", outlineSource, "outline_room")}
      </div>
    `;
  }
  el.projectBriefSummary.querySelectorAll("[data-project-summary-open]").forEach((node) => {
    node.addEventListener("click", async () => {
      try {
        await openOrCreateConversationScope(node.dataset.projectSummaryOpen);
      } catch (error) {
        setStatus(String(error.message || error), "error");
      }
    });
  });
  el.projectBriefSummary.querySelectorAll("[data-project-summary-apply]").forEach((node) => {
    node.addEventListener("click", async () => {
      try {
        await applyStageSummary(node.dataset.projectSummaryApply);
      } catch (error) {
        setStatus(String(error.message || error), "error");
      }
    });
  });
  el.projectBriefSummary.querySelectorAll("[data-apply-stage-summary]").forEach((node) => {
    node.addEventListener("click", async () => {
      try {
        await applyStageSummary(node.dataset.applyStageSummary);
      } catch (error) {
        setStatus(String(error.message || error), "error");
      }
    });
  });
}

function scopeNeedsRunContext(scope) {
  return ["chapter_planning", "rewrite_intervention", "chapter_retro"].includes(scope);
}

function preferredScopeForDecisionType(decisionType) {
  if (decisionType === "character_note") return "character_room";
  if (decisionType === "outline_constraint") return "outline_room";
  if (decisionType === "human_instruction") return "rewrite_intervention";
  if (decisionType === "chapter_card_patch") return "chapter_planning";
  return "project_bootstrap";
}

function threadSupportsDecisionType(scope, decisionType) {
  if (decisionType === "writer_playbook_rule") return ["project_bootstrap", "chapter_retro"].includes(scope);
  if (decisionType === "character_note") return scope === "character_room";
  if (decisionType === "outline_constraint") return scope === "outline_room";
  if (decisionType === "chapter_card_patch") return scope === "chapter_planning";
  if (decisionType === "human_instruction") return scope === "rewrite_intervention";
  return false;
}

function conversationGuidance(run) {
  return run?.request?.conversation_guidance || null;
}

function artifactRunRecord() {
  const runId = state.artifactRunId || state.selectedRunId;
  if (!runId) return null;
  return (state.projectSnapshot.runs || []).find((item) => item.run_id === runId) || null;
}

function groupedRunGuidance(run) {
  const guidance = conversationGuidance(run);
  const adopted = guidance?.adopted_decisions || [];
  const grouped = {
    characters: [],
    outline: [],
    long_term: [],
    chapter: [],
  };
  adopted.forEach((item) => {
    const text = compactDecisionText(item.summary, 52);
    if (!text) return;
    grouped[conversationDecisionGroup(item.decision_type)]?.push(text);
  });
  return grouped;
}

function formalLaunchInstruction(run) {
  const instruction = run?.request?.human_instruction || null;
  if (!instruction || instruction.requested_action !== "formal_launch") return null;
  const payload = instruction.payload || {};
  return {
    chapterFocus: payload.chapter_focus || null,
    launchNote: payload.launch_note || null,
  };
}

function artifactGuidanceBullets(artifactType) {
  const run = artifactRunRecord();
  if (!run) return [];
  const grouped = groupedRunGuidance(run);
  const formalLaunch = formalLaunchInstruction(run);
  const labels = [];
  if (["current_card", "planning_context", "current_draft", "drafting_context"].includes(artifactType)) {
    if (grouped.characters[0]) labels.push(`人物设定输入：${grouped.characters[0]}`);
    if (grouped.outline[0]) labels.push(`卷纲约束输入：${grouped.outline[0]}`);
    if (grouped.long_term[0]) labels.push(`长期规则输入：${grouped.long_term[0]}`);
    if (grouped.chapter[0]) labels.push(`本章修订输入：${grouped.chapter[0]}`);
  }
  if (formalLaunch?.chapterFocus && ["current_card", "planning_context"].includes(artifactType)) {
    labels.push(`本次系统优先照顾：${formalLaunch.chapterFocus}`);
  }
  if (formalLaunch?.chapterFocus && ["current_draft", "drafting_context", "publish_package"].includes(artifactType)) {
    labels.push(`正文阶段继续围绕：${formalLaunch.chapterFocus}`);
  }
  if (formalLaunch?.launchNote && ["current_draft", "drafting_context", "publish_package"].includes(artifactType)) {
    labels.push(`你还需要继续盯：${formalLaunch.launchNote}`);
  }
  return labels;
}

function formalLaunchReviewBullets() {
  const run = artifactRunRecord();
  const formalLaunch = formalLaunchInstruction(run);
  if (!run || !formalLaunch) return [];
  const phaseDecision = run.result?.phase_decision || {};
  const reviewTrace = run.result?.review_resolution_trace || {};
  const finalDecision = phaseDecision.final_decision || null;
  const unresolvedCount = reviewTrace.recurring_count ?? reviewTrace.open_count ?? 0;
  const bullets = [];

  if (formalLaunch.chapterFocus) {
    if (finalDecision === "pass" || finalDecision === "continue") {
      bullets.push(`启动重点当前判断：已初步兑现“${formalLaunch.chapterFocus}”。`);
    } else if (finalDecision === "rewrite" || finalDecision === "replan") {
      bullets.push(`启动重点当前判断：还没站稳“${formalLaunch.chapterFocus}”，本轮仍需继续修。`);
    } else if (finalDecision === "human_check") {
      bullets.push(`启动重点当前判断：围绕“${formalLaunch.chapterFocus}”仍需人工确认。`);
    } else if (unresolvedCount > 0) {
      bullets.push(`启动重点当前判断：仍有 ${unresolvedCount} 个问题未收口，暂时还不能算稳定兑现。`);
    } else {
      bullets.push(`启动重点当前判断：本轮已围绕“${formalLaunch.chapterFocus}”展开，但还要结合后续审校继续看。`);
    }
  }

  if (formalLaunch.launchNote) {
    if (finalDecision === "pass" || finalDecision === "continue") {
      bullets.push(`启动备注当前状态：暂未被判定为主要阻塞项。`);
    } else if (finalDecision === "rewrite" || finalDecision === "replan" || finalDecision === "human_check" || unresolvedCount > 0) {
      bullets.push(`启动备注当前仍需继续盯：${formalLaunch.launchNote}`);
    } else {
      bullets.push(`启动备注当前状态：已带入本轮判断，后续仍建议继续观察。`);
    }
  }

  return bullets;
}

function conversationGuidanceSummary(run) {
  const guidance = conversationGuidance(run);
  if (!guidance || !guidance.decision_count) return null;
  return `本次已带入 ${guidance.decision_count} 条对话结论`;
}

function reviewerLabel(value) {
  return REVIEWER_LABELS[value] || nodeLabel(REVIEWER_LABELS[value] ? "" : value) || value || "未记录";
}

function reviewerStatusText(value) {
  if (value === "completed") return "已返回";
  if (value === "running") return "审校中";
  return "待返回";
}

function reviewerStallLabel(reviewProgress) {
  if (!reviewProgress?.longest_wait_reviewer || !reviewProgress?.longest_wait_seconds) return null;
  return `${reviewerLabel(reviewProgress.longest_wait_reviewer)} · 已等待 ${formatDuration((reviewProgress.longest_wait_seconds || 0) * 1000)}`;
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

function remainingReviewers(reviewProgress) {
  return [...(reviewProgress.active_reviewers || []), ...(reviewProgress.pending_reviewers || [])];
}

function buildTimelineEntries(run) {
  const progress = run.result?.progress || {};
  const reviewProgress = progress.review_progress || {};
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
  if (reviewProgress.stage_status === "running" || reviewProgress.stage_status === "completed") {
    entries.push({
      title: `并行审校 ${reviewProgress.completed_count || 0}/${reviewProgress.total_count || 4}`,
      meta: reviewerStallLabel(reviewProgress)
        ? `当前最慢：${reviewerStallLabel(reviewProgress)}`
        : remainingReviewers(reviewProgress).length
          ? `等待：${remainingReviewers(reviewProgress).map((item) => reviewerLabel(item)).join("、")}`
        : "4 个审校都已返回",
      status: reviewProgress.stage_status === "completed" ? "done" : "current",
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

function chapterForRun(run) {
  const progress = run.result?.progress || {};
  const publish = run.result?.publish_package || {};
  const currentCard = run.result?.current_card || {};
  const feedbackSummary = run.result?.feedback_summary || {};
  return (
    progress.chapter_no
    || publish.chapter_no
    || currentCard.chapter_no
    || feedbackSummary.chapter_no
    || run.request?.target_chapters
    || 1
  );
}

function latestApprovalForRun(runId, approvals = state.projectSnapshot.approvals || []) {
  return approvals
    .filter((item) => item.run_id === runId)
    .sort((left, right) => right.created_at.localeCompare(left.created_at))[0] || null;
}

function latestExecutableApproval(approvals = state.projectSnapshot.approvals || []) {
  return approvals
    .filter((item) => item.status === "approved" && !item.executed_run_id)
    .sort((left, right) => right.created_at.localeCompare(left.created_at))[0] || null;
}

function runDisplayStatus(run, approvals = state.projectSnapshot.approvals || []) {
  if (run.status !== "awaiting_approval") {
    return run.status;
  }
  const approval = latestApprovalForRun(run.run_id, approvals);
  if (!approval) {
    return run.status;
  }
  if (approval.status === "approved") {
    return approval.executed_run_id ? "approved" : "awaiting_execution";
  }
  if (approval.status === "rejected") {
    return "rejected";
  }
  return run.status;
}

function summarizeRunCard(run) {
  const displayStatus = runDisplayStatus(run);
  const progress = run.result?.progress || {};
  const reviewProgress = progress.review_progress || {};
  const publish = run.result?.publish_package || {};
  const guidanceSummary = conversationGuidanceSummary(run);
  const checkpoint = humanCheckpoint(run);
  const stage = runStageSummary(run);
  if (run.status === "running") {
    if (reviewProgress.stage_status === "running") {
      return `${guidanceSummary ? `${guidanceSummary}；` : ""}${stage.stageLead} ${stage.stageDetail}`;
    }
    return `${guidanceSummary ? `${guidanceSummary}；` : ""}${stage.stageLead}`;
  }
  if (displayStatus === "awaiting_execution") {
    return `${guidanceSummary ? `${guidanceSummary}；` : ""}${stage.stageLead}`;
  }
  if (displayStatus === "approved") {
    return `${guidanceSummary ? `${guidanceSummary}；` : ""}${stage.stageLead}`;
  }
  if (displayStatus === "rejected") {
    return `${guidanceSummary ? `${guidanceSummary}；` : ""}${stage.stageLead}`;
  }
  if (displayStatus === "awaiting_approval") {
    return `${guidanceSummary ? `${guidanceSummary}；` : ""}${checkpoint?.thread_id ? "系统已自动创建人工检查点，可直接进入会诊；" : ""}${stage.stageLead}`;
  }
  if (run.status === "failed") {
    return run.result?.manual_intervention?.action === "auto_timeout"
      ? `${guidanceSummary ? `${guidanceSummary}；` : ""}${stage.stageLead}`
      : `${guidanceSummary ? `${guidanceSummary}；` : ""}${stage.stageLead}`;
  }
  if (run.status === "completed") {
    return publish.blurb || `${guidanceSummary ? `${guidanceSummary}；` : ""}${stage.stageLead}`;
  }
  return "查看这条运行的详细结果。";
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function summarizeArtifact(item) {
  const payload = item.payload || {};
  const guidanceBullets = artifactGuidanceBullets(item.artifact_type);
  const launchReviewBullets = ["latest_review_reports", "phase_decision", "review_resolution_trace", "human_guidance"].includes(item.artifact_type)
    ? formalLaunchReviewBullets()
    : [];
  if (item.artifact_type === "publish_package") {
    return {
      lead: `${payload.title || "未命名章节"} · 约 ${payload.word_count || 0} 字`,
      bullets: [
        ...guidanceBullets,
        payload.blurb ? `章节提要：${payload.blurb}` : null,
        payload.chapter_end_question ? `章末钩子：${payload.chapter_end_question}` : null,
        payload.operator_notes ? `操作备注：${payload.operator_notes}` : null,
      ].filter(Boolean),
      excerpt: payload.excerpt || payload.full_text || "",
    };
  }
  if (item.artifact_type === "current_draft") {
    return {
      lead: `${payload.title || "当前正文草稿"} · ${payload.summary_100w || "已生成正文草稿"}`,
      bullets: [
        ...guidanceBullets,
        ...(payload.risk_notes || []).slice(0, 4).map((note) => `风险提示：${note}`),
      ],
      excerpt: payload.content || "",
    };
  }
  if (item.artifact_type === "current_card") {
    return {
      lead: `第 ${payload.chapter_no || "?"} 章 · ${payload.purpose || "未记录章卡目的"}`,
      bullets: [
        ...guidanceBullets,
        payload.pov ? `视角：${payload.pov}` : null,
        ...(payload.must_include || []).slice(0, 3).map((itemValue) => `必须包含：${itemValue}`),
        ...(payload.must_not_change || []).slice(0, 2).map((itemValue) => `不可改动：${itemValue}`),
      ].filter(Boolean),
      excerpt: (payload.scene_beats || [])
        .slice(0, 3)
        .map((beat, index) => `场景${index + 1}：${beat.goal} / ${beat.conflict} / ${beat.turn}`)
        .join("\n"),
    };
  }
  if (item.artifact_type === "latest_review_reports") {
    const reports = Array.isArray(payload) ? payload : [];
    return {
      lead: reports.length ? `共 ${reports.length} 份审校意见` : "暂无审校意见",
      bullets: [
        ...launchReviewBullets,
        ...reports.slice(0, 4).map((report) => {
          const reviewer = artifactLabel(`${report.reviewer}_reviewer`).replace("_reviewer", "");
          return `${reviewer || report.reviewer}：${report.decision} / 总分 ${report.scores?.total ?? "?"}`;
        }),
      ],
      excerpt: reports[0]?.issues?.[0]
        ? `${reports[0].issues[0].evidence}\n建议：${reports[0].issues[0].fix_instruction}`
        : "",
    };
  }
  if (item.artifact_type === "phase_decision") {
    return {
      lead: `系统决定：${payload.final_decision || "未记录"}`,
      bullets: [
        ...launchReviewBullets,
        payload.reason ? `原因：${payload.reason}` : null,
        ...(payload.must_fix || []).slice(0, 4).map((entry) => `必须修复：${entry}`),
        ...(payload.can_defer || []).slice(0, 2).map((entry) => `可延后：${entry}`),
      ].filter(Boolean),
      excerpt: "",
    };
  }
  if (item.artifact_type === "creative_contract") {
    return {
      lead: `${payload.project?.working_title || "未命名作品"} · ${payload.project?.genre || "未记录题材"}`,
      bullets: [
        payload.reader_promise?.one_sentence_hook ? `一句话卖点：${payload.reader_promise.one_sentence_hook}` : null,
        ...(payload.non_negotiables?.must_have || []).slice(0, 3).map((entry) => `必须包含：${entry}`),
        ...(payload.non_negotiables?.must_not_have || []).slice(0, 2).map((entry) => `必须避免：${entry}`),
      ].filter(Boolean),
      excerpt: "",
    };
  }
  if (item.artifact_type === "story_bible") {
    return {
      lead: payload.premise || "故事设定已生成",
      bullets: [
        ...(payload.world_rules || []).slice(0, 3).map((entry) => `世界规则：${entry}`),
        ...(payload.factions || []).slice(0, 3).map((entry) => `势力：${entry}`),
      ],
      excerpt: (payload.character_cards || [])
        .slice(0, 3)
        .map((character) => `${character.role} ${character.character_id}：${character.desire}`)
        .join("\n"),
    };
  }
  if (item.artifact_type === "arc_plan") {
    return {
      lead: payload.arc_name || "卷纲已生成",
      bullets: [
        payload.arc_goal ? `卷目标：${payload.arc_goal}` : null,
        payload.conflict_core ? `核心冲突：${payload.conflict_core}` : null,
        ...(payload.milestones || []).slice(0, 3).map((entry) => `里程碑：${entry}`),
      ].filter(Boolean),
      excerpt: payload.climax_hook || "",
    };
  }
  if (item.artifact_type === "planning_context") {
    const applications = payload.issue_applications || [];
    return {
      lead: `章卡层已应用 ${(payload.applied_guardrails || []).length} 条防线`,
      bullets: [
        ...guidanceBullets,
        ...(payload.applied_guardrails || []).slice(0, 4).map((entry) => `已应用：${entry}`),
        ...applications.slice(0, 3).map((entry) => `问题 ${entry.issue_id || "unknown"}：${entry.applied_guardrail || entry.fix_instruction || "已前置规避"}`),
      ],
      excerpt: (payload.stubborn_issue_ids || []).slice(0, 3).join("\n"),
    };
  }
  if (item.artifact_type === "drafting_context") {
    const applications = payload.issue_applications || [];
    return {
      lead: `正文层已应用 ${(payload.applied_guardrails || []).length} 条防线`,
      bullets: [
        ...guidanceBullets,
        ...(payload.applied_guardrails || []).slice(0, 4).map((entry) => `已应用：${entry}`),
        ...(payload.must_include || []).slice(0, 2).map((entry) => `必须兑现：${entry}`),
        ...(payload.must_not_change || []).slice(0, 2).map((entry) => `不可破坏：${entry}`),
        ...applications.slice(0, 2).map((entry) => `问题 ${entry.issue_id || "unknown"}：${entry.applied_guardrail || entry.fix_instruction || "已在正文规避"}`),
      ],
      excerpt: (payload.addressed_issue_ids || []).slice(0, 4).join("\n"),
    };
  }
  if (item.artifact_type === "feedback_summary") {
    return {
      lead: `第 ${payload.chapter_no || "?"} 章结果已回收`,
      bullets: [
        ...(payload.immediate_actions || []).slice(0, 3).map((entry) => `立即执行：${entry}`),
        ...(payload.observe || []).slice(0, 2).map((entry) => `继续观察：${entry}`),
        ...(payload.discard || []).slice(0, 2).map((entry) => `避免复发：${entry}`),
        payload.playbook_version ? `写作手册版本：v${payload.playbook_version}` : null,
      ].filter(Boolean),
      excerpt: "",
    };
  }
  if (item.artifact_type === "chapter_lesson") {
    return {
      lead: `第 ${payload.chapter_no || "?"} 章经验卡 · 重写 ${payload.rewrite_count ?? 0} 次`,
      bullets: [
        payload.issue_progress_summary ? `账本进展：${payload.issue_progress_summary}` : null,
        ...(payload.pass_reasons || []).slice(0, 2).map((entry) => `通过原因：${entry}`),
        ...(payload.carry_forward_rules || []).slice(0, 3).map((entry) => `延续规则：${entry}`),
      ].filter(Boolean),
      excerpt: (payload.discarded_patterns || []).slice(0, 3).join("\n"),
    };
  }
  if (item.artifact_type === "writer_playbook") {
    return {
      lead: `写作手册 v${payload.version || 1} · 已更新到第 ${payload.last_chapter_no || "?"} 章`,
      bullets: [
        ...(payload.always_apply || []).slice(0, 4).map((entry) => `始终遵守：${entry}`),
        ...(payload.validated_patterns || []).slice(0, 2).map((entry) => `已验证有效：${entry}`),
      ],
      excerpt: (payload.watch_out || []).slice(0, 4).join("\n"),
    };
  }
  if (item.artifact_type === "issue_ledger") {
    const issues = payload.issues || [];
    return {
      lead: `问题账本 · ${payload.status || "unknown"} · 未关闭 ${payload.open_count ?? issues.length} 项`,
      bullets: [
        payload.progress_summary
          || `已解决 ${payload.resolved_count ?? 0} 项，复发 ${payload.recurring_count ?? 0} 项，新增 ${payload.new_count ?? 0} 项。`,
        ...issues.slice(0, 4).map((issue) => {
          const reviewer = issue.reviewer || "unknown";
          const severity = issue.severity || "minor";
          const status = issue.status || "open";
          return `${status} / ${reviewer} / ${severity}：${issue.fix_instruction || issue.evidence || issue.issue_id}`;
        }),
      ].filter(Boolean),
      excerpt: issues
        .slice(0, 3)
        .map((issue) => `${issue.category || "general"} / ${issue.status || "open"}：${issue.evidence || ""}`)
        .join("\n"),
    };
  }
  if (item.artifact_type === "review_resolution_trace") {
    const entries = payload.items || [];
    return {
      lead: `问题关闭证据 · 已解决 ${payload.resolved_count ?? 0} 项，复发 ${payload.recurring_count ?? 0} 项，新增 ${payload.new_count ?? 0} 项`,
      bullets: [
        ...launchReviewBullets,
        ...entries.slice(0, 4).map((entry) => {
          const reviewer = entry.reviewer || "unknown";
          const decision = entry.reviewer_decision || "未记录";
          return `${entry.status || "open"} / ${reviewer} / ${decision}：${entry.resolution_summary || entry.fix_instruction || entry.issue_id}`;
        }),
      ],
      excerpt: entries
        .slice(0, 3)
        .map((entry) => {
          const planning = entry.planning_application?.applied_guardrail;
          const drafting = entry.drafting_application?.applied_guardrail;
          return [entry.issue_id, planning, drafting].filter(Boolean).join("\n");
        })
        .join("\n\n"),
    };
  }
  if (item.artifact_type === "canon_state") {
    return {
      lead: `Canon 已更新到第 ${payload.story_clock?.current_chapter || "?"} 章`,
      bullets: [
        payload.story_clock?.current_arc ? `当前卷：${payload.story_clock.current_arc}` : null,
        `角色状态数：${Object.keys(payload.character_states || {}).length}`,
        `开放悬念数：${(payload.open_loops || []).length}`,
      ].filter(Boolean),
      excerpt: (payload.open_loops || []).slice(0, 3).map((loop) => `${loop.id}: ${loop.question}`).join("\n"),
    };
  }
  if (item.artifact_type === "human_guidance") {
    return {
      lead: payload.reason || "需要人工介入",
      bullets: [
        ...launchReviewBullets,
        ...(payload.must_fix || []).slice(0, 4).map((entry) => `必须修复：${entry}`),
        ...(payload.can_defer || []).slice(0, 2).map((entry) => `可延后：${entry}`),
      ],
      excerpt: "",
    };
  }
  if (item.artifact_type === "blockers") {
    const blockers = Array.isArray(payload) ? payload : [];
    return {
      lead: blockers.length ? `当前有 ${blockers.length} 个阻塞点` : "当前没有阻塞点",
      bullets: blockers.slice(0, 5),
      excerpt: "",
    };
  }
  if (item.artifact_type === "event_log") {
    const logs = Array.isArray(payload) ? payload : [];
    return {
      lead: logs.length ? `已记录 ${logs.length} 条事件` : "暂无事件",
      bullets: logs.slice(-5).map((entry) => eventLabel(entry)),
      excerpt: "",
    };
  }
  return {
    lead: "这是流程中的中间材料。",
    bullets: [],
    excerpt: "",
  };
}

function parseListField(value) {
  return String(value || "")
    .split(/\n|,/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function artifactPayload(items, artifactType) {
  return (items || []).find((item) => item.artifact_type === artifactType)?.payload || null;
}

function traceSourceLabel(sourceType) {
  const labels = {
    playbook: "项目写作手册",
    lesson: "上一章经验卡",
    pending_issue: "未关闭问题",
    chapter_card_required: "本章必须兑现",
    chapter_card_invariant: "本章不可破坏",
  };
  return labels[sourceType] || sourceType || "未知来源";
}

function buildLearningSummary(items) {
  const chapterLesson = artifactPayload(items, "chapter_lesson") || {};
  const writerPlaybook = artifactPayload(items, "writer_playbook") || {};
  const issueLedger = artifactPayload(items, "issue_ledger") || {};
  const reviewResolutionTrace = artifactPayload(items, "review_resolution_trace") || {};
  const planningContext = artifactPayload(items, "planning_context") || {};
  const draftingContext = artifactPayload(items, "drafting_context") || {};
  const currentCard = artifactPayload(items, "current_card") || {};
  const currentDraft = artifactPayload(items, "current_draft") || {};
  const latestReviewReports = artifactPayload(items, "latest_review_reports") || [];
  const pendingIssues = (issueLedger.issues || []).filter((issue) => ["open", "recurring"].includes(issue.status));
  const recurringIssues = pendingIssues.filter((issue) => issue.status === "recurring");
  const resolvedIssues = (reviewResolutionTrace.items || []).filter((item) => item.status === "resolved");
  const sourceLinkedRules = [
    ...((planningContext.guardrail_sources || []).slice(0, 3)),
    ...((draftingContext.guardrail_sources || []).slice(0, 3)),
  ];
  const exactApplications = [
    ...(planningContext.issue_applications || []).map((item) => `章卡层先处理 ${item.issue_id}：${item.applied_guardrail}`),
    ...(draftingContext.issue_applications || []).map((item) => `正文层继续处理 ${item.issue_id}：${item.applied_guardrail}`),
  ];
  const learningTrace = [
    {
      title: "章卡规划",
      status: planningContext.chapter_no ? "已应用" : "未应用",
      detail: planningContext.chapter_no
        ? `系统已在章卡层落地 ${(planningContext.applied_guardrails || []).length} 条防线。`
        : "还没有看到章卡生成结果。",
    },
    {
      title: "正文起草",
      status: draftingContext.chapter_no ? "已应用" : "未应用",
      detail: draftingContext.chapter_no
        ? `正文起草前已落地 ${(draftingContext.applied_guardrails || []).length} 条防线。`
        : "正文层还没有可见结果。",
    },
    {
      title: "审校复核",
      status: latestReviewReports.length ? "已应用" : "未应用",
      detail: latestReviewReports.length
        ? "审校已开始优先复查旧问题是否真正关闭。"
        : "审校层还没有返回结果。",
    },
    {
      title: "经验沉淀",
      status: chapterLesson.chapter_no || writerPlaybook.version ? "已应用" : "未应用",
      detail: chapterLesson.chapter_no || writerPlaybook.version
        ? "本章结果已经反哺经验卡和项目写作手册。"
        : "本章还没有完成经验回收。",
    },
  ];
  const appliedSteps = learningTrace.filter((item) => item.status === "已应用").length;

  return {
    learnedLead: chapterLesson.pass_reasons?.[0] || "系统还没有沉淀出明确的通过经验。",
    learnedItems: [
      ...sourceLinkedRules
        .slice(0, 4)
        .map((item) => `${traceSourceLabel(item.source_type)}：${item.guardrail}`),
      ...(writerPlaybook.validated_patterns || []).slice(0, 2).map((item) => `已验证有效：${item}`),
      ...(chapterLesson.pass_reasons || []).slice(0, 2).map((item) => `通过原因：${item}`),
    ].filter(Boolean),
    guardLead: pendingIssues.length
      ? `这次已提前纳入 ${pendingIssues.length} 个未关闭问题的规避要求。`
      : "当前没有未关闭旧问题需要额外规避。",
    guardItems: [
      ...exactApplications.slice(0, 4),
      ...pendingIssues.slice(0, 3).map((issue) => issue.fix_instruction || issue.evidence || issue.issue_id),
    ].filter(Boolean),
    riskLead: recurringIssues.length
      ? `仍有 ${recurringIssues.length} 个问题在反复出现，需要重点盯住。`
      : "当前没有明显反复出现的问题。",
    riskItems: [
      ...(writerPlaybook.watch_out || []).slice(0, 2),
      ...recurringIssues.slice(0, 3).map((issue) => `${issue.reviewer || "unknown"}：${issue.fix_instruction || issue.evidence || issue.issue_id}`),
      ...(chapterLesson.discarded_patterns || []).slice(0, 2),
    ].filter(Boolean),
    progressSummary: chapterLesson.issue_progress_summary || issueLedger.progress_summary || "",
    closureLead: resolvedIssues.length
      ? `这次已有 ${resolvedIssues.length} 个旧问题被确认关闭。`
      : "这次还没有看到明确关闭的旧问题。",
    closureItems: resolvedIssues.slice(0, 4).map((item) => {
      const planning = item.planning_application?.applied_guardrail;
      const drafting = item.drafting_application?.applied_guardrail;
      const proof = [planning ? `章卡：${planning}` : null, drafting ? `正文：${drafting}` : null]
        .filter(Boolean)
        .join("；");
      return `${item.issue_id} · ${item.confirmed_by || item.reviewer || "unknown"} 确认关闭。${proof ? ` ${proof}` : ""}`;
    }),
    traceLead: `这次运行里，学习闭环已经在 ${appliedSteps}/${learningTrace.length} 个环节落地。`,
    traceItems: learningTrace.map((item) => `${item.title} · ${item.status} · ${item.detail}`),
  };
}

function renderLearningPanel(run) {
  if (!run) {
    el.learningCaption.textContent = "需要先选中一个项目";
    el.learningPanel.innerHTML = `<div class="empty">当前没有可解释的学习结果。</div>`;
    return;
  }

  if (state.artifactRunId !== run.run_id) {
    el.learningCaption.textContent = `还没有加载第 ${chapterForRun(run)} 章的过程材料`;
    el.learningPanel.innerHTML = `<div class="empty">点击“查看工件”后，这里会告诉你系统学到了什么、规避了什么、还在担心什么。</div>`;
    return;
  }

  const learning = buildLearningSummary(state.artifactItems);
  el.learningCaption.textContent = learning.progressSummary || `当前对应第 ${chapterForRun(run)} 章的学习结果`;
  const cards = [
    {
      title: "系统学到了什么",
      lead: learning.learnedLead,
      items: learning.learnedItems,
    },
    {
      title: "这次主动规避什么",
      lead: learning.guardLead,
      items: learning.guardItems,
    },
    {
      title: "仍要警惕什么",
      lead: learning.riskLead,
      items: learning.riskItems,
    },
    {
      title: "哪些旧问题被怎样关闭",
      lead: learning.closureLead,
      items: learning.closureItems,
    },
    {
      title: "这次在哪些环节用了经验",
      lead: learning.traceLead,
      items: learning.traceItems,
    },
  ];
  el.learningPanel.innerHTML = cards
    .map(
      (section) => `
        <article class="learning-card">
          <h4>${section.title}</h4>
          <div class="learning-lead">${escapeHtml(section.lead)}</div>
          ${
            section.items.length
              ? `<ul class="learning-list">${section.items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
              : `<div class="meta">当前没有更多细节。</div>`
          }
        </article>
      `
    )
    .join("");
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
  const reviewProgress = progress.review_progress || {};
  const updatedAt = progress.updated_at ? formatTimestamp(progress.updated_at) : "未记录";
  const stageGoal = progress.stage_goal || "等待下一步目标。";
  const possibleCause = progress.possible_cause || null;
  const interventionAction = focusRun?.result?.manual_intervention?.action || null;
  const readiness = openingReadiness(project);

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
      disableQuickRunButton: true,
      runButtonLabel: "生成章节",
      quickRunButtonLabel: "快速试写",
    };
  }

  if (!latestChapter && !focusRun && !readiness.ready) {
    const missingLabels = readiness.items.filter((item) => !item.done).map((item) => item.label);
    return {
      goal: "先补齐开书确认，再开始正式首章。",
      system: "系统空闲，正在等待你把项目方向、人物设定和第一卷方向收紧成可执行摘要。",
      event: `当前还缺：${missingLabels.join("、")}。`,
      next: "去“项目设定”页补齐缺口；如果你只是想先试一下方向，可以点“快速试写”。",
      heroNote: "正式首章建议在三层摘要都齐了之后再开始，这样后面的章卡和正文会更稳。",
      pill: `开书确认 ${readiness.completed}/${readiness.total}`,
      kind: "warn",
      focusRun: null,
      disableRunButton: true,
      disableQuickRunButton: false,
      runButtonLabel: "先补齐开书确认",
      quickRunButtonLabel: "只做快速试写",
    };
  }

  if (focusRun?.status === "running") {
    const targetChapter = progress.chapter_no || latestChapter + 1 || 1;
    const stage = runStageSummary(focusRun);
    const staleMs = progress.updated_at ? Date.now() - new Date(progress.updated_at).getTime() : 0;
    const stale = staleMs > 180000;
    return {
      goal: `完成第 ${targetChapter} 章的生成。`,
      system: stage.stageLead,
      event: `${stage.stageDetail} 最近更新时间：${updatedAt}。`,
      next: stale
        ? `这条 Run 已经 ${formatDuration(staleMs)} 没有新进度。它更像是卡住，而不是一直重写。先点“刷新”确认；如果仍不动，就点“标记失败”，然后再“重新尝试”。`
        : stage.stageHint,
      heroNote: stale
        ? "系统判断这条运行更像是卡住，而不是正常生成中。建议先收口这条失败，再决定是否重试。"
        : stage.stageLead,
      pill: stale ? `Run 可能卡住: ${focusRun.run_id}` : stage.stagePill,
      kind: "warn",
      focusRun,
      disableRunButton: true,
      disableQuickRunButton: true,
      runButtonLabel: "生成中…",
      quickRunButtonLabel: "生成中…",
    };
  }

  if (pendingApproval) {
    const focusStage = focusRun ? runStageSummary(focusRun) : null;
    return {
      goal: "决定当前章节是否通过人工审批。",
      system: focusStage?.stageLead || "系统已暂停，等待人工决定。",
      event: focusStage?.stageDetail || `待处理审批：${pendingApproval.reason}`,
      next: "去“审批”栏选择接受当前方案，或先打回再讨论。接受后再按恢复路径执行。",
      heroNote: "现在系统不会继续自动写。你做出审批决定后，它才会进入下一步。",
      pill: "等待人工审批",
      kind: "warn",
      focusRun: focusRun || null,
      disableRunButton: true,
      disableQuickRunButton: true,
      runButtonLabel: "等待审批",
      quickRunButtonLabel: "等待审批",
    };
  }

  if (approvedWaitingExecution) {
    const focusStage = focusRun ? runStageSummary(focusRun) : null;
    return {
      goal: "启动已审批通过的续写任务。",
      system: focusStage?.stageLead || "系统等待你执行下一步续写。",
      event: focusStage?.stageDetail || `审批已通过，但尚未执行：${approvedWaitingExecution.approval_id}`,
      next: "在“审批”栏确认恢复路径无误后，点击对应执行按钮启动下一条后台 Run。",
      heroNote: "审批已经通过，但还没有开始续写。这里最重要的是启动下一条运行。",
      pill: "等待执行续写",
      kind: "warn",
      focusRun: focusRun || null,
      disableRunButton: true,
      disableQuickRunButton: true,
      runButtonLabel: "等待执行",
      quickRunButtonLabel: "等待执行",
    };
  }

  if (focusRun?.status === "failed") {
    const stage = runStageSummary(focusRun);
    return {
      goal: `重新尝试生成第 ${progress.chapter_no || latestChapter + 1 || 1} 章。`,
      system: stage.stageLead,
      event: stage.stageDetail,
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
      disableQuickRunButton: latestChapter > 0,
      runButtonLabel: "重新生成章节",
      quickRunButtonLabel: latestChapter > 0 ? "仅首章可用" : "快速试写",
    };
  }

  if (latestChapter > 0) {
    const stage = focusRun ? runStageSummary(focusRun) : null;
    return {
      goal: `复核已生成的第 ${latestChapter} 章结果。`,
      system: stage?.stageLead || "系统空闲，最近一次 Run 已完成。",
      event: stage?.stageDetail || `最近已生成到第 ${latestChapter} 章。`,
      next: "先查看当前章节工件和审校结果；如果没有待审批项且你想继续，可以再次点击“生成章节”。",
      heroNote: "当前没有阻塞。你可以先复核结果，再决定是否继续写下一章。",
      pill: "最近 Run 已完成",
      kind: "ready",
      focusRun,
      disableRunButton: false,
      disableQuickRunButton: true,
      runButtonLabel: "继续生成章节",
      quickRunButtonLabel: "仅首章可用",
    };
  }

  return {
    goal: "启动首章生成。",
    system: readiness.ready ? "系统空闲，已具备正式开书条件。" : "系统空闲。",
    event: readiness.ready ? "项目三层摘要已齐，可以正式进入首章。" : "项目已创建，但还没有任何章节和 Run。",
    next: readiness.ready ? "点击“以正式模式开始首章”，按完整项目摘要进入正式创作。" : "点击“生成章节”，启动第一个后台 Run。",
    heroNote: readiness.ready ? "这本书的项目方向、人物设定和第一卷方向已经形成摘要，适合用正式模式开始首章。" : "这是一个全新项目。先跑出第 1 章，再看系统给出的材料和建议。",
    pill: "可以开始生成",
    kind: "ready",
    focusRun: null,
    disableRunButton: false,
    disableQuickRunButton: false,
    runButtonLabel: readiness.ready ? "以正式模式开始首章" : "生成章节",
    quickRunButtonLabel: "只做快速试写",
  };
}

function deriveConversationAction() {
  const project = selectedProject();
  const thread = selectedThread();
  const focusRun = pickFocusRun(state.projectSnapshot.runs || []);
  const focusDisplayStatus = focusRun ? runDisplayStatus(focusRun) : null;
  const decisions = state.projectSnapshot.conversationDecisions || [];
  const threadDecisions = thread ? decisions.filter((item) => item.thread_id === thread.thread_id) : [];
  const executableApproval = latestExecutableApproval(state.projectSnapshot.approvals || []);
  const latestChapter = latestChapterNo(state.projectSnapshot.chapters || []);

  if (!project) {
    return { disabled: true, label: "按当前结论执行", copy: "先选择项目，才能用当前已采纳结论驱动下一步动作。", action: null };
  }
  if (!decisions.length) {
    return { disabled: true, label: "按当前结论执行", copy: "先把对话中的一条消息采纳为规则或修订指令，再执行。", action: null };
  }
  if (focusRun?.status === "running") {
    return { disabled: true, label: "Run 进行中", copy: "当前已有 Run 在执行。等它结束后，再决定是否带着这些结论继续下一步。", action: null };
  }
  if (thread?.scope === "rewrite_intervention") {
    const approval = latestApprovalForThread(thread);
    const selectedMode = inferRecoveryModeForThread(thread);
    const plan = recoveryModePlan(selectedMode, threadContext(thread));
    if (!approval) {
      return {
        disabled: true,
        label: recoveryModeExecuteLabel(selectedMode),
        copy: "当前会诊线程还没有绑定审批单。先等系统进入人工检查点，或从待处理审批进入对应会诊。",
        action: null,
      };
    }
    if (approval.status === "pending") {
      return {
        disabled: true,
        label: "先处理审批",
        copy: `当前已选恢复路径是“${recoveryModeLabel(selectedMode)}”，但审批还没通过。先在右侧审批区点“通过”或“驳回”。`,
        action: null,
      };
    }
    if (approval.status === "rejected") {
      return {
        disabled: true,
        label: "审批已驳回",
        copy: "这条人工检查点已经被驳回。建议先补充会诊结论，再重新提交新的处理动作。",
        action: null,
      };
    }
    if (approval.executed_run_id) {
      return {
        disabled: true,
        label: "本次会诊已执行",
        copy: `这条人工检查点已经按“${recoveryModeLabel(selectedMode)}”进入执行。请回到运行记录查看最新进展。`,
        action: null,
      };
    }
    return {
      disabled: false,
      label: recoveryModeExecuteLabel(selectedMode),
      copy: `${recoveryModeDescription(selectedMode)} 当前会保留：${plan.preserves[0]} 风险：${plan.risks[0]}`,
      action: { kind: "execute-approval", approvalId: approval.approval_id, recoveryMode: selectedMode },
    };
  }
  if (focusDisplayStatus === "awaiting_approval") {
    return { disabled: true, label: "等待审批", copy: "当前章节还在等待你的审批决定。先处理审批，再决定是否按这些结论继续执行。", action: null };
  }
  if (thread?.scope === "chapter_planning") {
    const patchCount = threadDecisions.filter((item) => item.decision_type === "chapter_card_patch").length;
    if (!patchCount) {
      return {
        disabled: true,
        label: "先确认章卡方向",
        copy: "这一条是章卡协商线程。先把至少一条消息采纳为“章卡修订”，再带着确认后的方向开写。",
        action: null,
      };
    }
    if (focusRun?.status === "failed") {
      return {
        disabled: false,
        label: "按章卡结论重试本章",
        copy: `这一章已确认 ${patchCount} 条章卡修订。现在重试会优先按这些写前结论重做本章。`,
        action: { kind: "retry-run", runId: focusRun.run_id },
      };
    }
    if (latestChapter > 0) {
      return {
        disabled: false,
        label: "按章卡结论继续下一章",
        copy: `当前章卡线程已确认 ${patchCount} 条修订。继续生成时会先带着这些写前结论进入下一章。`,
        action: { kind: "continue-run" },
      };
    }
    return {
      disabled: false,
      label: "按章卡结论开始首章",
      copy: `当前章卡线程已确认 ${patchCount} 条修订。开始首章时会优先按这些写前结论生成。`,
      action: { kind: "start-run" },
    };
  }
  if (executableApproval) {
    return {
      disabled: false,
      label: "按结论执行续写",
      copy: `当前已有已审批但未执行的续写。执行后会自动带上已采纳的对话结论。`,
      action: { kind: "execute-approval", approvalId: executableApproval.approval_id },
    };
  }
  if (focusRun?.status === "failed") {
    return {
      disabled: false,
      label: "按结论重试当前章",
      copy: `最新失败的是第 ${chapterForRun(focusRun)} 章。现在重试会自动带上已采纳的规则和修订指令。`,
      action: { kind: "retry-run", runId: focusRun.run_id },
    };
  }
  if (latestChapter > 0) {
    return {
      disabled: false,
      label: "按结论继续下一章",
      copy: `当前项目已生成到第 ${latestChapter} 章。继续生成时会自动带上已采纳的对话结论。`,
      action: { kind: "continue-run" },
    };
  }
  return {
    disabled: false,
    label: "按结论开始首章",
    copy: "当前还没有章节。开始首章时会自动带上已采纳的对话结论。",
    action: { kind: "start-run" },
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
  el.createRunQuick.disabled = summary.disableQuickRunButton;
  el.createRunQuick.textContent = summary.quickRunButtonLabel;
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

function renderReviewProgressCard(reviewProgress) {
  if (!reviewProgress || reviewProgress.stage_status === "not_started") {
    return "";
  }
  const reviewers = reviewProgress.reviewers || {};
  const items = Object.entries(reviewers).map(([name, item]) => {
      const status = item.status || "pending";
      const decision = item.decision || "等待返回";
      const totalScore = item.total_score ?? "?";
      const finishedAt = item.finished_at ? ` · ${formatTimestamp(item.finished_at)}` : "";
      const stallMeta = status === "running" && item.stalled_for_seconds
        ? ` · 已等待 ${formatDuration((item.stalled_for_seconds || 0) * 1000)}`
        : "";
      return `
      <div class="focus-metric">
        <strong>${reviewerLabel(name)}</strong>
        <div class="meta">${reviewerStatusText(status)}</div>
        <div class="meta">${status === "completed" ? `结论：${decision} / 总分 ${totalScore}` : status === "running" ? "并行执行中" : "等待返回"}</div>
        <div class="meta">${finishedAt || (item.started_at ? `开始于 ${formatTimestamp(item.started_at)}${stallMeta}` : "尚未开始")}</div>
      </div>
    `;
  });
  return `
    <div class="card">
      <div class="card-head">
        <h4>并行审校进度</h4>
        <div class="meta">已完成 ${reviewProgress.completed_count || 0}/${reviewProgress.total_count || 4}</div>
      </div>
      <div class="focus-run-grid">
        ${items.join("")}
      </div>
    </div>
  `;
}

function renderFocusRun(summary) {
  const run = summary.focusRun;
  if (!run) {
    el.focusRunCaption.textContent = "暂无活跃 Run";
    el.focusRun.innerHTML = `<div class="empty">当前没有需要重点关注的 Run。</div>`;
    return;
  }

  const progress = run.result?.progress || {};
  const reviewProgress = progress.review_progress || {};
  const logTail = progress.event_log_tail || [];
  const latestEvent = progress.latest_event || "暂无事件";
  const updatedAt = progress.updated_at || run.created_at;
  const staleMs = updatedAt ? Date.now() - new Date(updatedAt).getTime() : 0;
  const staleLabel = staleMs > 0 ? formatDuration(staleMs) : "未记录";
  const currentNode = nodeLabel(progress.current_node);
  const stage = runStageSummary(run);
  const stageGoal = progress.stage_goal || "未记录";
  const possibleCause = progress.possible_cause;
  const intervention = run.result?.manual_intervention || null;
  const displayStatus = runDisplayStatus(run);
  const guidance = conversationGuidance(run);
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
  const guidanceBlock = guidance?.decision_count
    ? `<div class="focus-metric"><strong>已带入对话结论</strong><div class="meta">${guidance.decision_count} 条，其中写作规则 ${guidance.writer_playbook_rule_count || 0} 条，人物设定 ${guidance.character_note_count || 0} 条，卷纲约束 ${guidance.outline_constraint_count || 0} 条，修订指令 ${guidance.human_instruction_count || 0} 条，章卡修订 ${guidance.chapter_card_patch_count || 0} 条。</div></div>`
    : "";
  const checkpoint = humanCheckpoint(run);
  const checkpointPlan = checkpoint ? recoveryModePlan(checkpoint.recommended_recovery_mode || "continue", checkpoint) : null;
  const checkpointBlock = checkpoint
    ? `<div class="focus-metric"><strong>人工检查点</strong><div class="meta">${escapeHtml(checkpoint.reason || "流程已暂停。")}${checkpoint.thread_id ? ` 已自动创建会诊线程。` : ""}</div><div class="meta">建议恢复路径：${recoveryModeLabel(checkpoint.recommended_recovery_mode || "continue")}</div>${checkpointPlan ? `<div class="meta">会保留：${escapeHtml(checkpointPlan.preserves[0])}</div><div class="meta">风险：${escapeHtml(checkpointPlan.risks[0])}</div>` : ""}</div>`
    : "";
  const actionButtons = [
    renderViewArtifactsButton(run.run_id, run.artifact_count),
  ];
  if (checkpoint?.thread_id) {
    actionButtons.push(`<button class="button ghost" data-action="open-thread" data-id="${checkpoint.thread_id}">进入会诊</button>`);
  }
  if (run.status === "running") {
    actionButtons.push(`<button class="button ghost" data-action="mark-failed" data-id="${run.run_id}">标记失败</button>`);
  }
  if (run.status === "failed") {
    actionButtons.push(`<button class="button ghost" data-action="retry-run" data-id="${run.run_id}">重新尝试</button>`);
  }

  el.focusRunCaption.textContent = `第 ${chapterForRun(run)} 章 · ${STATUS_LABELS[displayStatus] || displayStatus}`;
  el.focusRun.innerHTML = `
    <div class="card focus-run-hero">
      <div class="card-head">
        <h4>${stage.stageTitle}</h4>
        ${statusChip(displayStatus)}
      </div>
      <div class="meta">第 ${chapterForRun(run)} 章 · 最近更新 ${formatTimestamp(updatedAt)}</div>
      <div class="focus-run-lead">${stage.stageLead}</div>
      <div class="focus-run-brief">
        <div class="focus-metric">
          <strong>当前目标</strong>
          <div class="meta">${stageGoal}</div>
        </div>
        <div class="focus-metric">
          <strong>下一步建议</strong>
          <div class="meta">${stage.stageHint}</div>
        </div>
        <div class="focus-metric">
          <strong>最新事件</strong>
          <div class="meta">${latestEvent}</div>
        </div>
      </div>
      <div class="actions">
        ${actionButtons.join("")}
      </div>
    </div>
    <details class="focus-run-more">
      <summary>查看详细诊断</summary>
      <div class="focus-run-grid">
        <div class="focus-metric">
          <strong>当前阶段</strong>
          <div class="meta">${stage.stageTitle}</div>
        </div>
        <div class="focus-metric">
          <strong>章节</strong>
          <div class="meta">第 ${chapterForRun(run)} 章</div>
        </div>
        <div class="focus-metric">
          <strong>状态</strong>
          <div class="meta">${statusChip(displayStatus)}</div>
        </div>
        <div class="focus-metric">
          <strong>系统现在在做什么</strong>
          <div class="meta">${stage.stageLead}</div>
        </div>
        <div class="focus-metric">
          <strong>最近更新时间</strong>
          <div class="meta">${formatTimestamp(updatedAt)}</div>
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
          <strong>技术节点</strong>
          <div class="meta">${currentNode}</div>
        </div>
        ${guidanceBlock}
        ${checkpointBlock}
        ${interventionBlock}
        ${causeBlock}
        ${errorBlock}
      </div>
    </details>
    <details class="focus-run-more">
      <summary>查看阶段时间线</summary>
      <div class="card">
      <div class="card-head">
        <h4>阶段时间线</h4>
        ${statusChip(displayStatus)}
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
    </details>
    ${renderReviewProgressCard(reviewProgress)}
    <details class="focus-run-more">
      <summary>查看最近事件与带入结论</summary>
      <div class="card">
        <div class="card-head">
          <h4>最近事件尾部</h4>
          ${statusChip(displayStatus)}
        </div>
        <div class="meta">${logTail.length ? logTail.join(" -> ") : "暂无事件日志"}</div>
        ${
          guidance?.adopted_decisions?.length
            ? `<div class="meta">本次实际带入：${guidance.adopted_decisions
                .slice(0, 3)
                .map((item) => `${conversationDecisionLabel(item.decision_type)}：${escapeHtml(String(item.summary || "").slice(0, 24))}`)
                .join(" / ")}</div>`
            : ""
        }
      </div>
    </details>
  `;
  el.focusRun.querySelectorAll("[data-action]:not([disabled])").forEach((node) => {
    node.addEventListener("click", () => {
      if (node.dataset.action === "open-thread") {
        openConversationThread(node.dataset.id).catch((error) => setStatus(String(error.message || error), "error"));
        return;
      }
      handleRunAction(node.dataset.action, node.dataset.id);
    });
  });
}

function renderProjectState() {
  const project = selectedProject();
  const snapshot = state.projectSnapshot;
  renderProjectBriefSummary(project);
  renderProjectLaunchReadiness(project);
  renderChapters(snapshot.chapters || []);
  const focusRunId = pickFocusRun(snapshot.runs || [])?.run_id || null;
  const summary = deriveSummary(project, snapshot);
  renderOverview(project, snapshot, summary);
  renderRuns(snapshot.runs || [], focusRunId);
  renderApprovals(snapshot.approvals || []);
  renderSummary(summary);
  renderFocusRun(summary);
  renderLearningPanel(summary.focusRun || null);
  renderConversationPanel();
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
    const displayStatus = runDisplayStatus(item);
    const progress = item.result?.progress || {};
    const updatedAt = progress.updated_at || item.created_at;
    const stage = runStageSummary(item);
    const marker = stage.stageDetail || (item.status === "running"
      ? progress.latest_event || nodeLabel(progress.current_node) || "等待反馈"
      : item.error || progress.latest_event || "无附加信息");
    const chapterNo = chapterForRun(item);
    const classes = ["card"];
    if (item.run_id === state.selectedRunId || item.run_id === focusRunId) classes.push("active-run");
    if (recommendedCard) classes.push("recommended");
    if (!recommendedCard) classes.push("history");
    const actions = [renderViewArtifactsButton(item.run_id, item.artifact_count)];
    const checkpoint = humanCheckpoint(item);
    if ((recommendedCard || displayStatus === "awaiting_approval") && checkpoint?.thread_id) {
      actions.push(`<button class="button ghost" data-action="open-thread" data-id="${checkpoint.thread_id}">进入会诊</button>`);
    }
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
          <h4>第 ${chapterNo} 章 · ${stage.stageTitle}</h4>
          ${statusChip(displayStatus)}
        </div>
        <div class="meta">创建于 ${formatTimestamp(item.created_at)}</div>
        <div class="meta">${stage.stageLead}</div>
        <div class="meta">${summarizeRunCard(item)}</div>
        <div class="card-caption">${caption}</div>
        <details class="run-diagnostics">
          <summary>查看完整诊断</summary>
          <div class="meta">最近更新 ${formatTimestamp(updatedAt)} · 重写 ${progress.rewrite_count ?? 0} 次 · 工件 ${item.artifact_count ?? 0} 个</div>
          <div class="meta">运行标识：${item.run_id}</div>
          <div class="meta">当前诊断：${marker}</div>
          <div class="meta">阶段补充：${stage.stageDetail}</div>
          <div class="meta">系统建议：${stage.stageHint}</div>
        </details>
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
  el.runsList.querySelectorAll("[data-action]:not([disabled])").forEach((node) => {
    node.addEventListener("click", () => {
      if (node.dataset.action === "open-thread") {
        openConversationThread(node.dataset.id).catch((error) => setStatus(String(error.message || error), "error"));
        return;
      }
      handleRunAction(node.dataset.action, node.dataset.id);
    });
  });
}

function renderApprovals(items) {
  if (!items.length) {
    el.approvalsList.innerHTML = `<div class="empty">暂无审批单</div>`;
    return;
  }

  const approvalPriority = (item) => {
    if (item.status === "pending") return 0;
    if (item.status === "approved" && !item.executed_run_id) return 1;
    if (item.status === "rejected") return 2;
    if (item.status === "approved" && item.executed_run_id) return 3;
    return 4;
  };

  const sorted = [...items].sort((left, right) => {
    const diff = approvalPriority(left) - approvalPriority(right);
    if (diff !== 0) return diff;
    return new Date(right.created_at).getTime() - new Date(left.created_at).getTime();
  });

  const [focusApproval, ...historyApprovals] = sorted;
  const renderApprovalCard = (item, { recommendedCard = false } = {}) => {
    const actions = [];
    const interventionThread = conversationThreadForRun(item.run_id, "rewrite_intervention");
    const recoveryMode = interventionThread ? inferRecoveryModeForThread(interventionThread) : (isRecoveryMode(item.requested_action) ? item.requested_action : "continue");
    const recoveryPlan = recoveryModePlan(recoveryMode, { chapter_no: item.chapter_no });
    const title = approvalDecisionTitle(item, recoveryMode);
    const summary = approvalDecisionSummary(item, recoveryMode, recoveryPlan);
    const nextStep = approvalDecisionActions(item);
    if (item.status === "pending") {
      actions.push({ action: "approve", id: item.approval_id, label: "接受当前方案" });
      actions.push({ action: "reject", id: item.approval_id, label: "先打回再讨论" });
    }
    if (item.status === "approved" && !item.executed_run_id) {
      actions.push({ action: `execute-${recoveryMode}`, id: item.approval_id, label: recoveryModeExecuteLabel(recoveryMode) });
    }
    if (interventionThread) {
      actions.push({ action: "open-thread", id: interventionThread.thread_id, label: "进入会诊" });
    }
    const classes = ["card"];
    if (recommendedCard) classes.push("recommended");
    if (!recommendedCard) classes.push("history");
    return `
      <div class="${classes.join(" ")}">
        <div class="card-head">
          <h4>${title}</h4>
          <span class="status-chip status-${item.status}">${item.status === "approved" && !item.executed_run_id ? "待执行" : item.status}</span>
        </div>
        <div class="meta">${summary}</div>
        <div class="meta">${nextStep}</div>
        <div class="meta">当前恢复路径：${recoveryModeLabel(recoveryMode)}</div>
        <div class="meta">会保留：${escapeHtml(recoveryPlan.preserves[0])}</div>
        <div class="meta">会重做：${escapeHtml(recoveryPlan.rewrites[0])}</div>
        <div class="meta">风险：${escapeHtml(recoveryPlan.risks[0])}</div>
        ${item.executed_run_id ? `<div class="meta">已执行到：${item.executed_run_id}</div>` : ""}
        <div class="card-caption">${recommendedCard ? "这是当前最值得处理的一条审批决策。" : "历史审批记录，默认只用于参考。"}</div>
        <div class="actions">
          ${actions.map((action) => `<button class="button ghost" data-action="${action.action}" data-id="${action.id}">${action.label}</button>`).join("")}
        </div>
      </div>
    `;
  };

  const blocks = [`<div class="section-caption">当前推荐决策</div>${renderApprovalCard(focusApproval, { recommendedCard: true })}`];
  if (historyApprovals.length) {
    blocks.push(`
      <details class="approval-history">
        <summary>查看审批历史（${historyApprovals.length}）</summary>
        <div class="stack compact approval-history-body">
          ${historyApprovals.map((item) => renderApprovalCard(item)).join("")}
        </div>
      </details>
    `);
  }
  el.approvalsList.innerHTML = blocks.join("");
  el.approvalsList.querySelectorAll("[data-action]").forEach((node) => {
    node.addEventListener("click", () => {
      if (node.dataset.action === "open-thread") {
        openConversationThread(node.dataset.id).catch((error) => setStatus(String(error.message || error), "error"));
        return;
      }
      handleApprovalAction(node.dataset.action, node.dataset.id);
    });
  });
}

function artifactReadingSections(items) {
  const groups = [
    {
      key: "direction",
      title: "本章方向",
      description: "先看这一章到底想写什么、必须兑现什么、边界在哪里。",
      types: ["creative_contract", "story_bible", "arc_plan", "current_card", "planning_context", "human_guidance", "human_checkpoint", "blockers"],
    },
    {
      key: "draft",
      title: "正文进展",
      description: "再看正文是否成形，现在写到哪一步，已经能读到什么程度。",
      types: ["current_draft", "drafting_context", "publish_package"],
    },
    {
      key: "review",
      title: "审校结论",
      description: "这里解释为什么通过、为什么打回、当前卡在哪类问题。",
      types: ["latest_review_reports", "phase_decision", "review_resolution_trace"],
    },
    {
      key: "learning",
      title: "经验沉淀",
      description: "最后看这一章沉淀出了哪些经验、规则和后续注意事项。",
      types: ["feedback_summary", "chapter_lesson", "writer_playbook", "issue_ledger", "canon_state", "event_log"],
    },
  ];
  return groups
    .map((group) => ({
      ...group,
      items: items.filter((item) => group.types.includes(item.artifact_type)),
    }))
    .filter((group) => group.items.length);
}

function artifactSectionSpotlight(section) {
  const preferredTypes = {
    direction: ["current_card", "planning_context", "human_checkpoint", "human_guidance", "arc_plan", "creative_contract"],
    draft: ["publish_package", "current_draft", "drafting_context"],
    review: ["phase_decision", "review_resolution_trace", "latest_review_reports"],
    learning: ["chapter_lesson", "writer_playbook", "feedback_summary", "issue_ledger"],
  };
  const preferred = preferredTypes[section.key] || [];
  return preferred.map((type) => section.items.find((item) => item.artifact_type === type)).find(Boolean) || section.items[0];
}

function artifactSectionSummary(section) {
  const spotlight = artifactSectionSpotlight(section);
  const summary = summarizeArtifact(spotlight);
  const bullets = summary.bullets.slice(0, 2);
  return {
    spotlight,
    summary,
    bullets,
    meta: `本段 ${section.items.length} 份材料 · 建议先看：${artifactLabel(spotlight.artifact_type)}`,
  };
}

function renderArtifactExcerpt(item, summary) {
  if (!summary.excerpt) return "";
  const escaped = escapeHtml(summary.excerpt).replaceAll("\n", "<br>");
  const shouldCollapse = ["publish_package", "current_draft"].includes(item.artifact_type) && summary.excerpt.length > 280;
  if (!shouldCollapse) {
    return `<div class="artifact-excerpt">${escaped}</div>`;
  }
  const previewText = `${summary.excerpt.slice(0, 280).trimEnd()}...`;
  return `
    <div class="artifact-excerpt artifact-excerpt-preview">${escapeHtml(previewText).replaceAll("\n", "<br>")}</div>
    <details class="artifact-excerpt-more">
      <summary>${item.artifact_type === "publish_package" ? "展开全文" : "展开草稿全文"}</summary>
      <div class="artifact-excerpt artifact-excerpt-full">${escaped}</div>
    </details>
  `;
}

function renderArtifactCard(item, options = {}) {
  const summary = summarizeArtifact(item);
  const spotlightBadge = options.spotlight ? `<div class="section-caption">优先看这一项</div>` : "";
  const hint = item.artifact_type === "publish_package"
    ? "这是最接近对外可读结果的版本。"
    : item.artifact_type === "current_draft"
      ? "这是当前章节的正文草稿。"
      : item.artifact_type === "current_card"
        ? "这是系统准备写这一章前的章卡。"
        : item.artifact_type === "latest_review_reports"
          ? "这里能看到系统为什么判定通过、重写或重规划。"
          : "这是流程中的中间材料。";
  const bulletsHtml = summary.bullets.length
    ? `<ul class="artifact-bullets">${summary.bullets.map((entry) => `<li>${escapeHtml(entry)}</li>`).join("")}</ul>`
    : `<div class="meta">暂无进一步摘要</div>`;
  const excerptHtml = renderArtifactExcerpt(item, summary);
  return `
    <div class="card artifact-card ${options.spotlight ? "artifact-spotlight" : ""}">
      ${spotlightBadge}
      <h4>${artifactLabel(item.artifact_type)}</h4>
      <div class="meta">${formatTimestamp(item.created_at)}</div>
      <div class="card-caption">${hint}</div>
      <div class="artifact-summary">
        <div class="artifact-lead">${escapeHtml(summary.lead)}</div>
        ${bulletsHtml}
        ${excerptHtml}
      </div>
      <details class="artifact-raw">
        <summary>查看原始数据</summary>
        <pre>${escapeHtml(JSON.stringify(item.payload, null, 2))}</pre>
      </details>
    </div>
  `;
}

function renderArtifacts(items) {
  if (!items.length) {
    state.artifactItems = [];
    el.artifactsList.innerHTML = `<div class="empty">当前还没有可展示的过程材料</div>`;
    return;
  }

  const sorted = [...items].sort((left, right) => {
    const leftRank = ARTIFACT_ORDER.indexOf(left.artifact_type);
    const rightRank = ARTIFACT_ORDER.indexOf(right.artifact_type);
    return (leftRank === -1 ? 999 : leftRank) - (rightRank === -1 ? 999 : rightRank);
  });

  state.artifactItems = sorted;
  const sections = artifactReadingSections(sorted);
  el.artifactsList.innerHTML = sections
    .map((section) => {
      const info = artifactSectionSummary(section);
      const remainder = section.items.filter((item) => item !== info.spotlight);
      return `
        <section class="artifact-reading-section">
          <div class="artifact-reading-head">
            <div class="section-caption">${section.title}</div>
            <div class="muted">${section.description}</div>
            <div class="meta artifact-reading-meta">${info.meta}</div>
            <div class="artifact-reading-brief">
              <div class="artifact-reading-lead">${escapeHtml(info.summary.lead)}</div>
              ${info.bullets.length ? `<div class="artifact-reading-points">${info.bullets.map((entry) => `<span>${escapeHtml(entry)}</span>`).join("")}</div>` : ""}
            </div>
          </div>
          <div class="stack compact">
            ${renderArtifactCard(info.spotlight, { spotlight: true })}
            ${
              remainder.length
                ? `
                  <details class="artifact-reading-more">
                    <summary>查看其他材料（${remainder.length}）</summary>
                    <div class="stack compact artifact-reading-more-body">
                      ${remainder.map((item) => renderArtifactCard(item)).join("")}
                    </div>
                  </details>
                `
                : ""
            }
          </div>
        </section>
      `;
    })
    .join("");
}

function renderConversationThreads(items) {
  const focusRun = pickFocusRun(state.projectSnapshot.runs || []);
  CONVERSATION_SCENE_CONFIG.forEach(({ scope, element }) => {
    const node = el[element];
    if (!node) return;
    node.disabled = !state.selectedProjectId || (scopeNeedsRunContext(scope) && !focusRun);
  });
  if (!items.length) {
    el.conversationThreadList.innerHTML = `<div class="empty">还没有创作对话。你可以直接按上面的创作场景开一个线程。</div>`;
    return;
  }
  const sorted = [...items].sort((left, right) => {
    const leftSelected = left.thread_id === state.selectedThreadId ? 1 : 0;
    const rightSelected = right.thread_id === state.selectedThreadId ? 1 : 0;
    if (leftSelected !== rightSelected) return rightSelected - leftSelected;
    const leftOpen = left.status === "open" ? 1 : 0;
    const rightOpen = right.status === "open" ? 1 : 0;
    if (leftOpen !== rightOpen) return rightOpen - leftOpen;
    return new Date(right.updated_at || right.created_at).getTime() - new Date(left.updated_at || left.created_at).getTime();
  });

  const [focusThread, ...historyThreads] = sorted;
  const renderThreadCard = (item, { recommendedCard = false } = {}) => {
    const active = item.thread_id === state.selectedThreadId ? "active" : "";
    const chapterText = item.linked_chapter_no ? `第 ${item.linked_chapter_no} 章` : "项目级";
    const progressLabel = conversationThreadProgressLabel(item);
    const nextPrompt = interviewState(item)?.next_prompt;
    const classes = ["card", active];
    if (recommendedCard) classes.push("recommended");
    if (!recommendedCard) classes.push("history");
    return `
      <button class="${classes.filter(Boolean).join(" ")}" data-thread-id="${item.thread_id}">
        <div class="card-head">
          <h4>${item.title}</h4>
          <span class="status-chip status-${item.status}">${item.status === "open" ? "进行中" : item.status}</span>
        </div>
        <div class="meta">${conversationScopeLabel(item.scope)} · ${chapterText}</div>
        ${progressLabel ? `<div class="meta">采访进度 ${progressLabel}</div>` : ""}
        <div class="meta">${item.latest_message_preview || "还没有消息。"}</div>
        ${nextPrompt ? `<div class="card-caption">下一问：${escapeHtml(compactDecisionText(nextPrompt, 46))}</div>` : ""}
        <div class="card-caption">${recommendedCard ? "这是当前最值得继续的一条创作对话。" : "历史线程，默认只在需要时再展开查看。"}</div>
      </button>
    `;
  };

  const blocks = [`<div class="section-caption">当前会话</div>${renderThreadCard(focusThread, { recommendedCard: true })}`];
  if (historyThreads.length) {
    blocks.push(`
      <details class="conversation-thread-history">
        <summary>查看历史线程（${historyThreads.length}）</summary>
        <div class="stack compact conversation-thread-history-body">
          ${historyThreads.map((item) => renderThreadCard(item)).join("")}
        </div>
      </details>
    `);
  }
  el.conversationThreadList.innerHTML = blocks.join("");
  el.conversationThreadList.querySelectorAll("[data-thread-id]").forEach((node) => {
    node.addEventListener("click", () => {
      loadConversationMessages(node.dataset.threadId).catch((error) => setStatus(String(error.message || error), "error"));
    });
  });
}

function messageAdoptActions(thread, item) {
  if (!thread) return [];
  if (!["user", "assistant"].includes(item.role)) return [];
  if (thread.scope === "project_bootstrap") {
    return [{ label: "采纳为写作规则", decisionType: "writer_playbook_rule" }];
  }
  if (thread.scope === "character_room") {
    return [{ label: "采纳为人物设定", decisionType: "character_note" }];
  }
  if (thread.scope === "outline_room") {
    return [{ label: "采纳为卷纲约束", decisionType: "outline_constraint" }];
  }
  if (thread.scope === "chapter_planning") {
    return [{ label: "采纳为章卡修订", decisionType: "chapter_card_patch" }];
  }
  if (thread.scope === "rewrite_intervention") {
    return [
      { label: "采纳为修订指令", decisionType: "human_instruction" },
      { label: "采纳为章卡修订", decisionType: "chapter_card_patch" },
    ];
  }
  return [{ label: "采纳为写作规则", decisionType: "writer_playbook_rule" }];
}

function renderConversationMessages(items) {
  const thread = selectedThread();
  if (!items.length) {
    el.conversationMessageList.innerHTML = `<div class="empty">当前线程还没有消息。</div>`;
    return;
  }
  el.conversationMessageList.innerHTML = items
    .map((item) => {
      const actions = messageAdoptActions(thread, item);
      return `
      <article class="conversation-message ${item.role}">
        <div class="conversation-role">${conversationRoleLabel(item.role, item.message_type)} · ${formatTimestamp(item.created_at)}</div>
        <div class="conversation-content">${escapeHtml(item.content).replaceAll("\n", "<br>")}</div>
        ${
          actions.length
            ? `<div class="actions">${actions
                .map((action) => `<button class="button ghost" data-action="adopt-message" data-id="${item.message_id}" data-decision-type="${action.decisionType}">${action.label}</button>`)
                .join("")}</div>`
            : ""
        }
      </article>
    `;
    })
    .join("");
  el.conversationMessageList.querySelectorAll("[data-action='adopt-message']").forEach((node) => {
    node.addEventListener("click", () => adoptConversationMessage(node.dataset.id, node.dataset.decisionType));
  });
  el.conversationMessageList.scrollTop = el.conversationMessageList.scrollHeight;
}

function renderDecisionItemCard(item) {
  return `
    <div class="card decision-card">
      <div class="card-head">
        <h4>${conversationDecisionLabel(item.decision_type)}</h4>
        <span class="status-chip status-approved">已采纳</span>
      </div>
      <div class="meta">${formatTimestamp(item.created_at)}</div>
      <label class="decision-editor">
        <span class="muted">可直接编辑这条结论，保存后会进入后续运行。</span>
        <textarea data-decision-editor="${item.decision_id}" rows="4">${escapeHtml(editableDecisionContent(item))}</textarea>
      </label>
      <div class="actions">
        <button class="button ghost" data-action="save-decision" data-id="${item.decision_id}">保存修改</button>
        <button class="button ghost" data-action="delete-decision" data-id="${item.decision_id}">撤销采纳</button>
      </div>
    </div>
  `;
}

function createDecisionDraft(decisionType) {
  state.decisionDrafts = [
    {
      draftId: `draft_${Date.now()}_${Math.random().toString(16).slice(2, 8)}`,
      decisionType,
      content: "",
    },
    ...state.decisionDrafts,
  ];
  renderConversationPanel();
}

function cancelDecisionDraft(draftId) {
  state.decisionDrafts = state.decisionDrafts.filter((item) => item.draftId !== draftId);
  renderConversationPanel();
}

function updateDecisionDraftValue(draftId, value) {
  state.decisionDrafts = state.decisionDrafts.map((item) => (item.draftId === draftId ? { ...item, content: value } : item));
}

function renderDecisionDraftCard(item) {
  return `
    <div class="card decision-card draft">
      <div class="card-head">
        <h4>${draftDecisionLabel(item.decisionType)}</h4>
        <span class="status-chip status-pending">草稿</span>
      </div>
      <div class="meta">这是一条尚未保存的新结论。保存后会自动进入后续运行。</div>
      <label class="decision-editor">
        <span class="muted">直接输入你想新增的结论。</span>
        <textarea data-draft-editor="${item.draftId}" rows="4">${escapeHtml(item.content || "")}</textarea>
      </label>
      <div class="actions">
        <button class="button ghost" data-action="save-draft-decision" data-id="${item.draftId}" data-decision-type="${item.decisionType}">保存为结论</button>
        <button class="button ghost" data-action="cancel-draft-decision" data-id="${item.draftId}">取消</button>
      </div>
    </div>
  `;
}

function renderConversationDecisions(items) {
  const focusRun = pickFocusRun(state.projectSnapshot.runs || []);
  const groups = [
    {
      key: "characters",
      title: "人物",
      description: "主角气质、角色边界、人物关系张力等长期影响角色塑造的结论。",
      createLabel: "新建人物设定",
      createType: "character_note",
    },
    {
      key: "outline",
      title: "大纲",
      description: "第一卷主线、升级路径、卷末高潮等会影响整体推进的约束。",
      createLabel: "新建卷纲约束",
      createType: "outline_constraint",
    },
    {
      key: "long_term",
      title: "长期规则",
      description: "对整本书都应长期生效的写作偏好和硬规则。",
      createLabel: "新建长期规则",
      createType: "writer_playbook_rule",
    },
    {
      key: "chapter",
      title: "本章修订",
      description: "只针对当前章节或当前一次修稿生效的执行指令。",
      createLabel: "新建本章修订",
      createType: "human_instruction",
    },
  ];
  const itemsByGroup = Object.fromEntries(groups.map((group) => [group.key, []]));
  items.forEach((item) => {
    itemsByGroup[conversationDecisionGroup(item.decision_type)]?.push(item);
  });
  const draftsByGroup = Object.fromEntries(groups.map((group) => [group.key, []]));
  state.decisionDrafts.forEach((item) => {
    draftsByGroup[conversationDecisionGroup(item.decisionType)]?.push(item);
  });

  const hasAnyContent = items.length || state.decisionDrafts.length;
  el.conversationDecisionList.innerHTML = groups
    .map((group) => {
      const groupItems = itemsByGroup[group.key] || [];
      const groupDrafts = draftsByGroup[group.key] || [];
      const summary = summarizeDecisionGroup(groupItems, groupDrafts);
      const applied = summarizeAppliedGuidanceGroup(focusRun, group.key);
      const primaryDraft = groupDrafts[0] || null;
      const remainingDrafts = primaryDraft ? groupDrafts.slice(1) : [];
      const primaryItem = groupItems[0] || null;
      const remainingItems = primaryItem ? groupItems.slice(1) : [];
      const primaryCard = primaryDraft
        ? renderDecisionDraftCard(primaryDraft)
        : primaryItem
          ? renderDecisionItemCard(primaryItem)
          : `<div class="empty">这一组暂时还没有结论。</div>`;
      const secondaryCount = remainingDrafts.length + remainingItems.length;
      return `
        <section class="decision-group">
          <div class="decision-group-head">
            <div>
              <div class="section-caption">${group.title}</div>
              <div class="muted">${group.description}</div>
              <div class="decision-group-summary">
                <span class="decision-summary-pill">已采纳 ${summary.adoptedCount} 条</span>
                ${summary.draftCount ? `<span class="decision-summary-pill warn">草稿 ${summary.draftCount} 条</span>` : ""}
                ${
                  applied.appliedCount
                    ? `<span class="decision-summary-pill active">本次运行已用 ${applied.appliedCount} 条</span>`
                    : ""
                }
                ${
                  summary.highlights.length
                    ? summary.highlights
                        .map((item) => `<span class="decision-summary-pill ${item.draft ? "draft" : ""}">${escapeHtml(item.text)}</span>`)
                        .join("")
                    : `<span class="decision-summary-pill muted">当前还没有核心结论</span>`
                }
                ${
                  applied.highlights.length
                    ? applied.highlights
                        .map((item) => `<span class="decision-summary-pill active-subtle">${escapeHtml(item)}</span>`)
                        .join("")
                    : ""
                }
              </div>
            </div>
            <button class="button ghost" data-action="create-draft-decision" data-decision-type="${group.createType}">${group.createLabel}</button>
          </div>
          <div class="stack compact">
            ${primaryCard}
            ${
              secondaryCount
                ? `
                  <details class="decision-group-history">
                    <summary>查看本组其他结论（${secondaryCount}）</summary>
                    <div class="stack compact decision-group-history-body">
                      ${remainingDrafts.map((item) => renderDecisionDraftCard(item)).join("")}
                      ${remainingItems.map((item) => renderDecisionItemCard(item)).join("")}
                    </div>
                  </details>
                `
                : ""
            }
          </div>
        </section>
      `;
    })
    .join("");
  if (!hasAnyContent) {
    el.conversationDecisionList.insertAdjacentHTML("afterbegin", `<div class="empty">当前还没有采纳结果。你可以从任意一组直接新建空白结论，或者把对话消息采纳进来。</div>`);
  }
  el.conversationDecisionList.querySelectorAll("[data-action='save-decision']").forEach((node) => {
    node.addEventListener("click", () => updateConversationDecision(node.dataset.id));
  });
  el.conversationDecisionList.querySelectorAll("[data-action='delete-decision']").forEach((node) => {
    node.addEventListener("click", () => deleteConversationDecision(node.dataset.id));
  });
  el.conversationDecisionList.querySelectorAll("[data-action='create-draft-decision']").forEach((node) => {
    node.addEventListener("click", () => createDecisionDraft(node.dataset.decisionType));
  });
  el.conversationDecisionList.querySelectorAll("[data-action='cancel-draft-decision']").forEach((node) => {
    node.addEventListener("click", () => cancelDecisionDraft(node.dataset.id));
  });
  el.conversationDecisionList.querySelectorAll("[data-draft-editor]").forEach((node) => {
    node.addEventListener("input", () => updateDecisionDraftValue(node.dataset.draftEditor, node.value));
  });
  el.conversationDecisionList.querySelectorAll("[data-action='save-draft-decision']").forEach((node) => {
    node.addEventListener("click", () => saveDecisionDraft(node.dataset.id, node.dataset.decisionType));
  });
}

function renderConversationPanel() {
  const threads = state.projectSnapshot.conversationThreads || [];
  renderConversationThreads(threads);
  renderConversationDecisions(state.projectSnapshot.conversationDecisions || []);
  const thread = selectedThread();
  const actionPlan = deriveConversationAction();
  el.conversationThreadCaption.textContent = thread
    ? `${thread.title} · ${conversationScopeLabel(thread.scope)}`
    : "未选择线程";
  el.conversationCaption.textContent = state.selectedProjectId
    ? "用对话逐步收敛创作结论，并把人工判断沉淀成可执行上下文。"
    : "先选择项目，才能进入创作对话。";
  el.conversationActionCopy.textContent = actionPlan.copy;
  el.conversationExecute.disabled = actionPlan.disabled;
  el.conversationExecute.textContent = actionPlan.label;
  el.conversationExecute.dataset.actionKind = actionPlan.action?.kind || "";
  el.conversationExecute.dataset.runId = actionPlan.action?.runId || "";
  el.conversationExecute.dataset.approvalId = actionPlan.action?.approvalId || "";
  el.conversationExecute.dataset.recoveryMode = actionPlan.action?.recoveryMode || "";
  el.conversationInput.placeholder = conversationInputPlaceholder(thread);
  renderInterviewSummary(thread);
  renderThreadContext(thread);
  renderConversationMessages(state.conversationMessages || []);
  el.conversationSend.disabled = !thread;
  if (!thread && !state.conversationMessages.length) {
    el.conversationInterviewSummary.innerHTML = "";
    el.conversationThreadContext.innerHTML = "";
    el.conversationMessageList.innerHTML = `<div class="empty">先在当前项目中创建一条创作对话线程。</div>`;
  }
}

function fingerprintArtifacts(items) {
  return JSON.stringify(
    (items || []).map((item) => ({
      artifact_id: item.artifact_id,
      artifact_type: item.artifact_type,
      chapter_no: item.chapter_no,
      payload: item.payload,
    }))
  );
}

function renderArtifactsLoading(runId) {
  el.selectedRunLabel.textContent = `${runId} · 正在加载`;
  el.artifactsList.innerHTML = `<div class="empty">正在加载这条运行的过程材料…</div>`;
}

function scrollArtifactsIntoView() {
  setWorkspaceTab("artifacts");
}

async function loadConversationMessages(threadId, { activateTab = true } = {}) {
  state.selectedThreadId = threadId;
  if (activateTab) {
    setWorkspaceTab("conversation");
  }
  renderProjectState();
  const messages = await api(`/api/conversation-threads/${threadId}/messages`);
  state.conversationMessages = messages;
  renderConversationPanel();
}

async function openConversationThread(threadId) {
  if (!threadId) return;
  state.selectedThreadId = threadId;
  setWorkspaceTab("conversation");
  await loadConversationMessages(threadId, { activateTab: true });
  setStatus("已进入人工协作线程", "ready");
}

function conversationThreadBody(scope) {
  const focusRun = pickFocusRun(state.projectSnapshot.runs || []);
  const body = { scope };
  if (scopeNeedsRunContext(scope) && focusRun) {
    body.linked_run_id = focusRun.run_id;
    body.linked_chapter_no = chapterForRun(focusRun);
  }
  return body;
}

async function createConversationThread(scope) {
  if (!state.selectedProjectId) return;
  setWorkspaceTab("conversation");
  const body = conversationThreadBody(scope);
  const thread = await api(`/api/projects/${state.selectedProjectId}/conversation-threads`, {
    method: "POST",
    body: JSON.stringify(body),
  });
  await selectProject(state.selectedProjectId);
  state.selectedThreadId = thread.thread_id;
  await loadConversationMessages(thread.thread_id, { activateTab: true });
  setStatus(`已创建${conversationScopeLabel(scope)}线程`, "ready");
}

function inferIdeaProjectName(title, seed) {
  const cleanTitle = String(title || "").trim();
  if (cleanTitle) return cleanTitle;
  const excerpt = compactDecisionText(seed || "", 18).replace(/[：:，。,.\s]/g, "");
  if (excerpt) {
    return `灵感_${excerpt}`;
  }
  return `新书灵感_${new Date().toISOString().slice(0, 10)}`;
}

async function createIdeaProject(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const formData = new FormData(form);
  const title = String(formData.get("title") || "").trim();
  const ideaSeed = String(formData.get("idea_seed") || "").trim();
  const ideaSeedType = String(formData.get("idea_seed_type") || "scene").trim();
  const readerPull = String(formData.get("reader_pull") || "").trim();
  if (!ideaSeed) {
    setStatus("请先写下你脑子里最清楚的一点点想法。", "error");
    return;
  }
  try {
    const projectName = inferIdeaProjectName(title, ideaSeed);
    const defaultUserBrief = {
      title: title || projectName,
      idea_seed: ideaSeed,
      idea_seed_type: ideaSeedType,
      capture_stage: "seed",
      hook: "",
      genre: "",
      platform: "",
      must_have: [],
      must_not_have: [],
    };
    if (readerPull) {
      defaultUserBrief.intent_profile = { reader_pull: readerPull };
    }
    const project = await api("/api/projects", {
      method: "POST",
      body: JSON.stringify({
        name: projectName,
        description: compactDecisionText(ideaSeed, 120) || null,
        default_target_chapters: 1,
        default_user_brief: defaultUserBrief,
      }),
    });
    const thread = await api(`/api/projects/${project.project_id}/conversation-threads`, {
      method: "POST",
      body: JSON.stringify({ scope: "project_bootstrap" }),
    });
    form.reset();
    await loadProjects();
    await selectProject(project.project_id);
    state.selectedThreadId = thread.thread_id;
    await loadConversationMessages(thread.thread_id, { activateTab: true });
    await loadAudit();
    setWorkspaceTab("conversation");
    setStatus("项目已从灵感创建，并已进入立项共创线程。", "ready");
  } catch (error) {
    setStatus(String(error.message || error), "error");
  }
}

async function ensureThreadForDecisionType(decisionType) {
  setWorkspaceTab("conversation");
  const current = selectedThread();
  if (current && threadSupportsDecisionType(current.scope, decisionType)) {
    return current;
  }
  const existing = (state.projectSnapshot.conversationThreads || []).find((item) => threadSupportsDecisionType(item.scope, decisionType));
  if (existing) {
    state.selectedThreadId = existing.thread_id;
    await loadConversationMessages(existing.thread_id, { activateTab: true });
    return existing;
  }
  const scope = preferredScopeForDecisionType(decisionType);
  if (scopeNeedsRunContext(scope) && !pickFocusRun(state.projectSnapshot.runs || [])) {
    throw new Error("当前还没有可关联的章节运行，请先生成或选择一条章节运行。");
  }
  const thread = await api(`/api/projects/${state.selectedProjectId}/conversation-threads`, {
    method: "POST",
    body: JSON.stringify(conversationThreadBody(scope)),
  });
  await selectProject(state.selectedProjectId);
  state.selectedThreadId = thread.thread_id;
  await loadConversationMessages(thread.thread_id, { activateTab: true });
  return thread;
}

async function sendConversationMessage(event) {
  event.preventDefault();
  await submitConversationMessage(el.conversationInput.value.trim());
}

async function submitConversationMessage(content) {
  if (!state.selectedThreadId) return;
  if (!content) return;
  try {
    await api(`/api/conversation-threads/${state.selectedThreadId}/messages`, {
      method: "POST",
      body: JSON.stringify({ content }),
    });
    el.conversationInput.value = "";
    await selectProject(state.selectedProjectId);
    if (state.selectedThreadId) {
      await loadConversationMessages(state.selectedThreadId, { activateTab: false });
    }
    setStatus("对话已记录，并已生成下一步协作提示", "ready");
  } catch (error) {
    setStatus(String(error.message || error), "error");
  }
}

async function adoptConversationMessage(messageId, decisionType) {
  try {
    await api(`/api/conversation-messages/${messageId}/adopt`, {
      method: "POST",
      body: JSON.stringify({ decision_type: decisionType }),
    });
    await selectProject(state.selectedProjectId);
    if (state.selectedThreadId) {
      await loadConversationMessages(state.selectedThreadId, { activateTab: false });
    }
    setStatus(`已采纳为${conversationDecisionLabel(decisionType)}`, "ready");
  } catch (error) {
    setStatus(String(error.message || error), "error");
  }
}

async function createConversationDecisionFromDraft({ threadId, decisionType, content, sourceLabel }) {
  await api(`/api/conversation-threads/${threadId}/decisions`, {
    method: "POST",
    body: JSON.stringify({
      decision_type: decisionType,
      content,
      source_label: sourceLabel,
    }),
  });
  await selectProject(state.selectedProjectId);
  if (state.selectedThreadId) {
    await loadConversationMessages(state.selectedThreadId, { activateTab: false });
  }
  setStatus(`已从草案采纳为${conversationDecisionLabel(decisionType)}`, "ready");
}

async function applyStageSummary(threadId) {
  if (!threadId) return;
  await api(`/api/conversation-threads/${threadId}/apply-stage-summary`, {
    method: "POST",
  });
  await loadProjects();
  if (state.selectedProjectId) {
    await selectProject(state.selectedProjectId);
  }
  if (state.selectedThreadId) {
    await loadConversationMessages(state.selectedThreadId, { activateTab: false });
  }
  setWorkspaceTab("project");
  setStatus("已把这版阶段摘要写回项目设定", "ready");
}

async function splitStageSummary(threadId) {
  if (!threadId) return;
  const created = await api(`/api/conversation-threads/${threadId}/split-stage-summary`, {
    method: "POST",
  });
  await selectProject(state.selectedProjectId);
  if (state.selectedThreadId) {
    await loadConversationMessages(state.selectedThreadId, { activateTab: false });
  }
  const counts = created.reduce((acc, item) => {
    acc[item.decision_type] = (acc[item.decision_type] || 0) + 1;
    return acc;
  }, {});
  setStatus(
    `已拆出 ${created.length} 条结论：人物设定 ${counts.character_note || 0} / 卷纲约束 ${counts.outline_constraint || 0} / 长期规则 ${counts.writer_playbook_rule || 0}`,
    "ready"
  );
}

async function updateConversationDecision(decisionId) {
  const editor = el.conversationDecisionList.querySelector(`[data-decision-editor="${decisionId}"]`);
  const content = editor?.value.trim() || "";
  if (!content) {
    setStatus("结论内容不能为空", "error");
    return;
  }
  try {
    await api(`/api/conversation-decisions/${decisionId}`, {
      method: "PATCH",
      body: JSON.stringify({ content }),
    });
    await selectProject(state.selectedProjectId);
    if (state.selectedThreadId) {
      await loadConversationMessages(state.selectedThreadId, { activateTab: false });
    }
    setStatus("已更新对话结论", "ready");
  } catch (error) {
    setStatus(String(error.message || error), "error");
  }
}

async function deleteConversationDecision(decisionId) {
  if (!window.confirm("确认撤销这条已采纳结论吗？撤销后它将不再进入后续运行。")) {
    return;
  }
  try {
    await api(`/api/conversation-decisions/${decisionId}`, { method: "DELETE" });
    await selectProject(state.selectedProjectId);
    if (state.selectedThreadId) {
      await loadConversationMessages(state.selectedThreadId, { activateTab: false });
    }
    setStatus("已撤销这条采纳结论", "warn");
  } catch (error) {
    setStatus(String(error.message || error), "error");
  }
}

async function saveDecisionDraft(draftId, decisionType) {
  const editor = el.conversationDecisionList.querySelector(`[data-draft-editor="${draftId}"]`);
  const content = editor?.value.trim() || "";
  if (!content) {
    setStatus("结论内容不能为空", "error");
    return;
  }
  try {
    const thread = await ensureThreadForDecisionType(decisionType);
    const createdMessages = await api(`/api/conversation-threads/${thread.thread_id}/messages`, {
      method: "POST",
      body: JSON.stringify({ content }),
    });
    const sourceMessage = createdMessages[0];
    await api(`/api/conversation-messages/${sourceMessage.message_id}/adopt`, {
      method: "POST",
      body: JSON.stringify({ decision_type: decisionType }),
    });
    state.decisionDrafts = state.decisionDrafts.filter((item) => item.draftId !== draftId);
    await selectProject(state.selectedProjectId);
    if (state.selectedThreadId) {
      await loadConversationMessages(state.selectedThreadId, { activateTab: false });
    }
    setStatus(`已新增${conversationDecisionLabel(decisionType)}`, "ready");
  } catch (error) {
    setStatus(String(error.message || error), "error");
  }
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
  state.decisionDrafts = [];
  renderProjects();
  const project = state.projects.find((item) => item.project_id === projectId);
  el.projectTitle.textContent = project?.name || "未选择项目";
  el.projectMeta.textContent = project ? `${project.project_id}` : "选择左侧项目后查看详情";
  if (!project) {
    renderProjectState();
    return;
  }

  const [chapters, runs, approvals, conversationThreads, conversationDecisions] = await Promise.all([
    api(`/api/projects/${projectId}/chapters`),
    api(`/api/projects/${projectId}/runs`),
    api(`/api/projects/${projectId}/approval-requests`),
    api(`/api/projects/${projectId}/conversation-threads`),
    api(`/api/projects/${projectId}/conversation-decisions`),
  ]);
  state.projectSnapshot = { chapters, runs, approvals, conversationThreads, conversationDecisions };
  const knownRun = runs.find((item) => item.run_id === state.selectedRunId);
  if (!knownRun) {
    state.selectedRunId = pickFocusRun(runs)?.run_id || null;
  }
  const knownThread = conversationThreads.find((item) => item.thread_id === state.selectedThreadId);
  if (!knownThread) {
    state.selectedThreadId = conversationThreads[0]?.thread_id || null;
    state.conversationMessages = [];
  }
  renderProjectState();
  if (state.selectedRunId) {
    await loadArtifacts(state.selectedRunId);
  } else {
    el.selectedRunLabel.textContent = "未选择 Run";
    state.artifactRunId = null;
    state.artifactFingerprint = "";
    state.artifactItems = [];
    renderArtifacts([]);
  }
  if (state.selectedThreadId) {
    await loadConversationMessages(state.selectedThreadId, { activateTab: false });
  } else {
    state.conversationMessages = [];
    renderConversationPanel();
  }
}

async function loadArtifacts(
  runId,
  {
    showLoading = false,
    scrollOnSuccess = false,
    updateStatus = false,
  } = {}
) {
  state.selectedRunId = runId;
  renderProjectState();
  if (showLoading) {
    renderArtifactsLoading(runId);
  }
  if (updateStatus) {
    setStatus(`正在加载 ${runId} 的过程材料…`);
  }
  try {
    const artifacts = await api(`/api/runs/${runId}/artifacts`);
    const fingerprint = fingerprintArtifacts(artifacts);
    const shouldRender = state.artifactRunId !== runId || state.artifactFingerprint !== fingerprint;
    if (shouldRender) {
      renderArtifacts(artifacts);
      state.artifactRunId = runId;
      state.artifactFingerprint = fingerprint;
      renderLearningPanel(state.projectSnapshot.runs.find((item) => item.run_id === runId) || null);
    }
    const run = state.projectSnapshot.runs.find((item) => item.run_id === runId);
    const chapterText = run ? `第 ${chapterForRun(run)} 章` : runId;
    el.selectedRunLabel.textContent = `${chapterText} · ${runId}`;
    if (updateStatus) {
      setStatus(
        artifacts.length
          ? `已加载 ${chapterText} 的过程材料`
          : `${chapterText} 当前还没有可展示的过程材料`,
        artifacts.length ? "ready" : "warn"
      );
    }
    if (scrollOnSuccess) {
      scrollArtifactsIntoView();
    }
  } catch (error) {
    state.artifactRunId = runId;
    state.artifactFingerprint = "";
    state.artifactItems = [];
    el.selectedRunLabel.textContent = `${runId} · 加载失败`;
    el.artifactsList.innerHTML = `<div class="empty">过程材料加载失败：${escapeHtml(String(error.message || error))}</div>`;
    setStatus(`加载 ${runId} 的过程材料失败：${String(error.message || error)}`, "error");
    throw error;
  }
}

async function handleRunAction(action, runId) {
  if (action === "view-run") {
    try {
      setWorkspaceTab("artifacts");
      await loadArtifacts(runId, { showLoading: true, scrollOnSuccess: true, updateStatus: true });
    } catch (_error) {
      // loadArtifacts already updates the visible error state and status pill.
    }
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

async function handleApprovalAction(action, approvalId, options = {}) {
  try {
    setWorkspaceTab("approvals");
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
    if (action === "execute" || action.startsWith("execute-")) {
      const recoveryMode = isRecoveryMode(options.recoveryMode)
        ? options.recoveryMode
        : (action.startsWith("execute-") ? action.replace("execute-", "") : "");
      const payload = await api(`/api/approval-requests/${approvalId}/execute`, {
        method: "POST",
        ...(isRecoveryMode(recoveryMode)
          ? { body: JSON.stringify({ requested_action_override: recoveryMode }) }
          : {}),
      });
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
    setWorkspaceTab("dashboard");
    setStatus("项目已创建并已切换到新项目", "ready");
  } catch (error) {
    setStatus(String(error.message || error), "error");
  }
}

async function createRun({ quickMode = false, chapterFocus = null, launchNote = null } = {}) {
  if (!state.selectedProjectId) return;
  try {
    setWorkspaceTab("dashboard");
    const body = { operator_id: state.operatorId, quick_mode: quickMode };
    if (!quickMode && chapterFocus) {
      body.chapter_focus = chapterFocus;
    }
    if (!quickMode && launchNote && String(launchNote).trim()) {
      body.launch_note = String(launchNote).trim();
    }
    const payload = await api(`/api/projects/${state.selectedProjectId}/runs`, {
      method: "POST",
      body: JSON.stringify(body),
    });
    state.selectedRunId = payload.run_id;
    await selectProject(state.selectedProjectId);
    const completedRun = await waitForRunCompletion(payload.run_id);
    await selectProject(state.selectedProjectId);
    await loadAudit();
    if (completedRun) {
      setStatus(quickMode ? "快速试写已完成" : "正式首章已启动并完成当前运行");
    } else {
      setStatus(`${quickMode ? "快速试写" : "正式模式首章"} 仍在后台执行，可稍后刷新查看: ${payload.run_id}`, "warn");
    }
  } catch (error) {
    setStatus(String(error.message || error), "error");
  }
}

async function executeConversationAction() {
  const kind = el.conversationExecute.dataset.actionKind;
  if (!kind || el.conversationExecute.disabled) return;
  if (kind === "execute-approval") {
    await handleApprovalAction("execute", el.conversationExecute.dataset.approvalId, {
      recoveryMode: el.conversationExecute.dataset.recoveryMode,
    });
    return;
  }
  if (kind === "retry-run") {
    await handleRunAction("retry-run", el.conversationExecute.dataset.runId);
    return;
  }
  if (kind === "continue-run" || kind === "start-run") {
    await createRun({ quickMode: false });
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
  if (!el.workspacePages.some((node) => node.dataset.workspacePage === state.activeWorkspaceTab)) {
    state.activeWorkspaceTab = "dashboard";
  }
  renderWorkspaceTab();
  el.apiToken.value = state.apiToken;
  el.operatorId.value = state.operatorId;
  el.workspaceTabs.forEach((node) => {
    node.addEventListener("click", () => setWorkspaceTab(node.dataset.workspaceTab));
  });
  el.saveAuth.addEventListener("click", saveAuth);
  el.refreshProjects.addEventListener("click", () => loadProjects().catch((error) => setStatus(error.message, "error")));
  el.refreshAudit.addEventListener("click", () => loadAudit().catch((error) => setStatus(error.message, "error")));
  el.ideaCaptureForm.addEventListener("submit", createIdeaProject);
  el.projectForm.addEventListener("submit", createProject);
  el.createRun.addEventListener("click", () => createRun({ quickMode: false }));
  el.createRunQuick.addEventListener("click", () => createRun({ quickMode: true }));
  el.conversationExecute.addEventListener("click", () => executeConversationAction().catch((error) => setStatus(String(error.message || error), "error")));
  el.conversationCreateBootstrap.addEventListener("click", () => createConversationThread("project_bootstrap").catch((error) => setStatus(String(error.message || error), "error")));
  el.conversationCreateCharacters.addEventListener("click", () => createConversationThread("character_room").catch((error) => setStatus(String(error.message || error), "error")));
  el.conversationCreateOutline.addEventListener("click", () => createConversationThread("outline_room").catch((error) => setStatus(String(error.message || error), "error")));
  el.conversationCreatePlanning.addEventListener("click", () => createConversationThread("chapter_planning").catch((error) => setStatus(String(error.message || error), "error")));
  el.conversationCreateRewrite.addEventListener("click", () => createConversationThread("rewrite_intervention").catch((error) => setStatus(String(error.message || error), "error")));
  el.conversationCreateRetro.addEventListener("click", () => createConversationThread("chapter_retro").catch((error) => setStatus(String(error.message || error), "error")));
  el.conversationForm.addEventListener("submit", sendConversationMessage);

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
