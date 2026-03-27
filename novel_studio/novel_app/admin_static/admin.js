const state = {
  projects: [],
  selectedProjectId: null,
  selectedRunId: null,
  selectedThreadId: null,
  artifactRunId: null,
  artifactFingerprint: "",
  artifactItems: [],
  conversationMessages: [],
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
  projectForm: document.getElementById("project-form"),
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
  conversationCreateContext: document.getElementById("conversation-create-context"),
  conversationThreadList: document.getElementById("conversation-thread-list"),
  conversationDecisionList: document.getElementById("conversation-decision-list"),
  conversationThreadCaption: document.getElementById("conversation-thread-caption"),
  conversationActionCopy: document.getElementById("conversation-action-copy"),
  conversationExecute: document.getElementById("conversation-execute"),
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
  project_bootstrap: "项目共创",
  chapter_planning: "章卡协商",
  rewrite_intervention: "修稿协作",
  chapter_retro: "章节复盘",
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

function nodeLabel(value) {
  return NODE_LABELS[value] || value || "未记录";
}

function conversationScopeLabel(value) {
  return CONVERSATION_SCOPE_LABELS[value] || value || "创作对话";
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
  if (value === "chapter_card_patch") return "章卡修订";
  return value || "已采纳结论";
}

function conversationGuidance(run) {
  return run?.request?.conversation_guidance || null;
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
  if (run.status === "running") {
    if (reviewProgress.stage_status === "running") {
      return `${guidanceSummary ? `${guidanceSummary}；` : ""}4 个审校正在并行进行，已完成 ${reviewProgress.completed_count || 0}/${reviewProgress.total_count || 4}。`;
    }
    return `${guidanceSummary ? `${guidanceSummary}；` : ""}系统正在 ${nodeLabel(progress.current_node)}。`;
  }
  if (displayStatus === "awaiting_execution") {
    return `${guidanceSummary ? `${guidanceSummary}；` : ""}这一章已经审批通过，等待你执行继续写下一章。`;
  }
  if (displayStatus === "approved") {
    return `${guidanceSummary ? `${guidanceSummary}；` : ""}这一章已经审批通过，后续续写运行已启动或已完成。`;
  }
  if (displayStatus === "rejected") {
    return `${guidanceSummary ? `${guidanceSummary}；` : ""}这一章的审批已驳回，建议先看工件再决定是否重试。`;
  }
  if (displayStatus === "awaiting_approval") {
    return `${guidanceSummary ? `${guidanceSummary}；` : ""}这一章已经生成，正在等你决定是否继续。`;
  }
  if (run.status === "failed") {
    return run.result?.manual_intervention?.action === "auto_timeout"
      ? `${guidanceSummary ? `${guidanceSummary}；` : ""}这次运行长时间无进度，系统已自动收口。`
      : `${guidanceSummary ? `${guidanceSummary}；` : ""}这次运行没有顺利完成。`;
  }
  if (run.status === "completed") {
    return publish.blurb || `${guidanceSummary ? `${guidanceSummary}；` : ""}这一章已经生成完成，可先阅读结果。`;
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
  if (item.artifact_type === "publish_package") {
    return {
      lead: `${payload.title || "未命名章节"} · 约 ${payload.word_count || 0} 字`,
      bullets: [
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
      bullets: (payload.risk_notes || []).slice(0, 4).map((note) => `风险提示：${note}`),
      excerpt: payload.content || "",
    };
  }
  if (item.artifact_type === "current_card") {
    return {
      lead: `第 ${payload.chapter_no || "?"} 章 · ${payload.purpose || "未记录章卡目的"}`,
      bullets: [
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
      bullets: reports.slice(0, 4).map((report) => {
        const reviewer = artifactLabel(`${report.reviewer}_reviewer`).replace("_reviewer", "");
        return `${reviewer || report.reviewer}：${report.decision} / 总分 ${report.scores?.total ?? "?"}`;
      }),
      excerpt: reports[0]?.issues?.[0]
        ? `${reports[0].issues[0].evidence}\n建议：${reports[0].issues[0].fix_instruction}`
        : "",
    };
  }
  if (item.artifact_type === "phase_decision") {
    return {
      lead: `系统决定：${payload.final_decision || "未记录"}`,
      bullets: [
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
      bullets: entries.slice(0, 4).map((entry) => {
        const reviewer = entry.reviewer || "unknown";
        const decision = entry.reviewer_decision || "未记录";
        return `${entry.status || "open"} / ${reviewer} / ${decision}：${entry.resolution_summary || entry.fix_instruction || entry.issue_id}`;
      }),
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

  if (focusRun?.status === "running") {
    const targetChapter = progress.chapter_no || latestChapter + 1 || 1;
    const currentNode = progress.current_node || "等待节点反馈";
    const latestEvent = progress.latest_event || "run_started";
    const staleMs = progress.updated_at ? Date.now() - new Date(progress.updated_at).getTime() : 0;
    const stale = staleMs > 180000;
    return {
      goal: `完成第 ${targetChapter} 章的生成。`,
      system: reviewProgress.stage_status === "running"
        ? `系统正在并行审校，已完成 ${reviewProgress.completed_count || 0}/${reviewProgress.total_count || 4}；当前目标是：${stageGoal}`
        : `系统正在后台执行，当前节点是 ${currentNode}；当前目标是：${stageGoal}`,
      event: reviewProgress.stage_status === "running"
        ? `最近事件：${latestEvent}；${reviewerStallLabel(reviewProgress) ? `当前最慢的是 ${reviewerStallLabel(reviewProgress)}` : remainingReviewers(reviewProgress).length ? `仍在等待 ${remainingReviewers(reviewProgress).map((item) => reviewerLabel(item)).join("、")}` : "等待最后汇总"}；最近更新时间：${updatedAt}。`
        : `最近事件：${latestEvent}；最近更新时间：${updatedAt}；当前重写次数：${progress.rewrite_count ?? 0}。`,
      next: stale
        ? `这条 Run 已经 ${formatDuration(staleMs)} 没有新进度。它更像是卡住，而不是一直重写。先点“刷新”确认；如果仍不动，就点“标记失败”，然后再“重新尝试”。`
        : reviewProgress.stage_status === "running"
        ? `当前 4 个审校在并行工作，不要重复点击“生成章节”。等待自动刷新，留意哪些审校已返回、还剩谁没回。`
          : `当前已经有 Run 在执行，不要重复点击“生成章节”。等待自动刷新，或点“查看工件”跟踪当前 Run。`,
      heroNote: stale
        ? "系统判断这条运行更像是卡住，而不是正常生成中。建议先收口这条失败，再决定是否重试。"
        : reviewProgress.stage_status === "running"
          ? "当前不是串行审核，而是 4 个审校并行中。最重要的是看还有谁没返回。"
          : "当前已经在写作流程中。你现在最需要做的是观察，不是重复点击。",
      pill: stale ? `Run 可能卡住: ${focusRun.run_id}` : reviewProgress.stage_status === "running" ? `并行审校中 ${reviewProgress.completed_count || 0}/${reviewProgress.total_count || 4}` : `Run 执行中: ${currentNode}`,
      kind: "warn",
      focusRun,
      disableRunButton: true,
      disableQuickRunButton: true,
      runButtonLabel: "生成中…",
      quickRunButtonLabel: "生成中…",
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
      disableQuickRunButton: true,
      runButtonLabel: "等待审批",
      quickRunButtonLabel: "等待审批",
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
      disableQuickRunButton: true,
      runButtonLabel: "等待执行",
      quickRunButtonLabel: "等待执行",
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
      disableQuickRunButton: latestChapter > 0,
      runButtonLabel: "重新生成章节",
      quickRunButtonLabel: latestChapter > 0 ? "仅首章可用" : "快速试写",
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
      disableQuickRunButton: true,
      runButtonLabel: "继续生成章节",
      quickRunButtonLabel: "仅首章可用",
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
    disableQuickRunButton: false,
    runButtonLabel: "生成章节",
    quickRunButtonLabel: "快速试写",
  };
}

function deriveConversationAction() {
  const project = selectedProject();
  const focusRun = pickFocusRun(state.projectSnapshot.runs || []);
  const focusDisplayStatus = focusRun ? runDisplayStatus(focusRun) : null;
  const decisions = state.projectSnapshot.conversationDecisions || [];
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
  if (focusDisplayStatus === "awaiting_approval") {
    return { disabled: true, label: "等待审批", copy: "当前章节还在等待你的审批决定。先处理审批，再决定是否按这些结论继续执行。", action: null };
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
    ? `<div class="focus-metric"><strong>已带入对话结论</strong><div class="meta">${guidance.decision_count} 条，其中写作规则 ${guidance.writer_playbook_rule_count || 0} 条，修订指令 ${guidance.human_instruction_count || 0} 条，章卡修订 ${guidance.chapter_card_patch_count || 0} 条。</div></div>`
    : "";
  const actionButtons = [
    renderViewArtifactsButton(run.run_id, run.artifact_count),
  ];
  if (run.status === "running") {
    actionButtons.push(`<button class="button ghost" data-action="mark-failed" data-id="${run.run_id}">标记失败</button>`);
  }
  if (run.status === "failed") {
    actionButtons.push(`<button class="button ghost" data-action="retry-run" data-id="${run.run_id}">重新尝试</button>`);
  }

  el.focusRunCaption.textContent = `第 ${chapterForRun(run)} 章 · ${STATUS_LABELS[displayStatus] || displayStatus}`;
  el.focusRun.innerHTML = `
    <div class="focus-run-grid">
      <div class="focus-metric">
        <strong>章节</strong>
        <div class="meta">第 ${chapterForRun(run)} 章</div>
      </div>
      <div class="focus-metric">
        <strong>状态</strong>
        <div class="meta">${statusChip(displayStatus)}</div>
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
      ${guidanceBlock}
      ${interventionBlock}
      ${causeBlock}
      ${errorBlock}
    </div>
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
    ${renderReviewProgressCard(reviewProgress)}
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
      <div class="actions">
        ${actionButtons.join("")}
      </div>
    </div>
  `;
  el.focusRun.querySelectorAll("[data-action]:not([disabled])").forEach((node) => {
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
    const marker = item.status === "running"
      ? progress.latest_event || nodeLabel(progress.current_node) || "等待反馈"
      : item.error || progress.latest_event || "无附加信息";
    const chapterNo = chapterForRun(item);
    const classes = ["card"];
    if (item.run_id === state.selectedRunId || item.run_id === focusRunId) classes.push("active-run");
    if (recommendedCard) classes.push("recommended");
    if (!recommendedCard) classes.push("history");
    const actions = [renderViewArtifactsButton(item.run_id, item.artifact_count)];
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
          <h4>第 ${chapterNo} 章 · ${STATUS_LABELS[displayStatus] || displayStatus}</h4>
          ${statusChip(displayStatus)}
        </div>
        <div class="meta">创建于 ${formatTimestamp(item.created_at)} · ${item.run_id}</div>
        <div class="meta">最近更新 ${formatTimestamp(updatedAt)} · 重写 ${progress.rewrite_count ?? 0} 次 · 工件 ${item.artifact_count ?? 0} 个</div>
        <div class="meta">${summarizeRunCard(item)}</div>
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
  el.runsList.querySelectorAll("[data-action]:not([disabled])").forEach((node) => {
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
  el.artifactsList.innerHTML = sorted
    .map((item) => {
      const summary = summarizeArtifact(item);
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
      const excerptHtml = summary.excerpt
        ? `<div class="artifact-excerpt">${escapeHtml(summary.excerpt).replaceAll("\n", "<br>")}</div>`
        : "";
      return `
        <div class="card artifact-card">
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
    })
    .join("");
}

function renderConversationThreads(items) {
  el.conversationCreateBootstrap.disabled = !state.selectedProjectId;
  const focusRun = pickFocusRun(state.projectSnapshot.runs || []);
  el.conversationCreateContext.disabled = !state.selectedProjectId || !focusRun;
  if (!items.length) {
    el.conversationThreadList.innerHTML = `<div class="empty">还没有创作对话。你可以先发起项目共创，或基于当前 Run 发起协作。</div>`;
    return;
  }
  el.conversationThreadList.innerHTML = items
    .map((item) => {
      const active = item.thread_id === state.selectedThreadId ? "active" : "";
      const chapterText = item.linked_chapter_no ? `第 ${item.linked_chapter_no} 章` : "项目级";
      return `
        <button class="card ${active}" data-thread-id="${item.thread_id}">
          <div class="card-head">
            <h4>${item.title}</h4>
            <span class="status-chip status-${item.status}">${item.status === "open" ? "进行中" : item.status}</span>
          </div>
          <div class="meta">${conversationScopeLabel(item.scope)} · ${chapterText}</div>
          <div class="meta">${item.latest_message_preview || "还没有消息。"}</div>
        </button>
      `;
    })
    .join("");
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

function renderConversationDecisions(items) {
  if (!items.length) {
    el.conversationDecisionList.innerHTML = `<div class="empty">当前还没有采纳结果。你可以把对话里的结论采纳为规则或修订指令。</div>`;
    return;
  }
  el.conversationDecisionList.innerHTML = items
    .map((item) => `
      <div class="card">
        <div class="card-head">
          <h4>${conversationDecisionLabel(item.decision_type)}</h4>
          <span class="status-chip status-approved">已采纳</span>
        </div>
        <div class="meta">${formatTimestamp(item.created_at)}</div>
        <div class="meta">${escapeHtml(item.payload.comment || item.payload.rule || item.payload.instruction || item.payload.content || "已记录")}</div>
      </div>
    `)
    .join("");
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
  renderConversationMessages(state.conversationMessages || []);
  el.conversationSend.disabled = !thread;
  if (!thread && !state.conversationMessages.length) {
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
  artifactsPanel()?.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function loadConversationMessages(threadId) {
  state.selectedThreadId = threadId;
  renderProjectState();
  const messages = await api(`/api/conversation-threads/${threadId}/messages`);
  state.conversationMessages = messages;
  renderConversationPanel();
}

async function createConversationThread(scope) {
  if (!state.selectedProjectId) return;
  const focusRun = pickFocusRun(state.projectSnapshot.runs || []);
  const body = { scope };
  if (scope !== "project_bootstrap" && focusRun) {
    body.linked_run_id = focusRun.run_id;
    body.linked_chapter_no = chapterForRun(focusRun);
  }
  const thread = await api(`/api/projects/${state.selectedProjectId}/conversation-threads`, {
    method: "POST",
    body: JSON.stringify(body),
  });
  await selectProject(state.selectedProjectId);
  state.selectedThreadId = thread.thread_id;
  await loadConversationMessages(thread.thread_id);
  setStatus(`已创建${conversationScopeLabel(scope)}线程`, "ready");
}

async function sendConversationMessage(event) {
  event.preventDefault();
  if (!state.selectedThreadId) return;
  const content = el.conversationInput.value.trim();
  if (!content) return;
  try {
    await api(`/api/conversation-threads/${state.selectedThreadId}/messages`, {
      method: "POST",
      body: JSON.stringify({ content }),
    });
    el.conversationInput.value = "";
    await selectProject(state.selectedProjectId);
    if (state.selectedThreadId) {
      await loadConversationMessages(state.selectedThreadId);
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
      await loadConversationMessages(state.selectedThreadId);
    }
    setStatus(`已采纳为${conversationDecisionLabel(decisionType)}`, "ready");
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
    await loadConversationMessages(state.selectedThreadId);
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

async function createRun({ quickMode = false } = {}) {
  if (!state.selectedProjectId) return;
  try {
    const payload = await api(`/api/projects/${state.selectedProjectId}/runs`, {
      method: "POST",
      body: JSON.stringify({ operator_id: state.operatorId, quick_mode: quickMode }),
    });
    state.selectedRunId = payload.run_id;
    await selectProject(state.selectedProjectId);
    const completedRun = await waitForRunCompletion(payload.run_id);
    await selectProject(state.selectedProjectId);
    await loadAudit();
    if (completedRun) {
      setStatus(quickMode ? "快速试写已完成" : "Run 已完成");
    } else {
      setStatus(`${quickMode ? "快速试写" : "Run"} 仍在后台执行，可稍后刷新查看: ${payload.run_id}`, "warn");
    }
  } catch (error) {
    setStatus(String(error.message || error), "error");
  }
}

async function executeConversationAction() {
  const kind = el.conversationExecute.dataset.actionKind;
  if (!kind || el.conversationExecute.disabled) return;
  if (kind === "execute-approval") {
    await handleApprovalAction("execute", el.conversationExecute.dataset.approvalId);
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
  el.apiToken.value = state.apiToken;
  el.operatorId.value = state.operatorId;
  el.saveAuth.addEventListener("click", saveAuth);
  el.refreshProjects.addEventListener("click", () => loadProjects().catch((error) => setStatus(error.message, "error")));
  el.refreshAudit.addEventListener("click", () => loadAudit().catch((error) => setStatus(error.message, "error")));
  el.projectForm.addEventListener("submit", createProject);
  el.createRun.addEventListener("click", () => createRun({ quickMode: false }));
  el.createRunQuick.addEventListener("click", () => createRun({ quickMode: true }));
  el.conversationExecute.addEventListener("click", () => executeConversationAction().catch((error) => setStatus(String(error.message || error), "error")));
  el.conversationCreateBootstrap.addEventListener("click", () => createConversationThread("project_bootstrap").catch((error) => setStatus(String(error.message || error), "error")));
  el.conversationCreateContext.addEventListener("click", () => {
    const focusRun = pickFocusRun(state.projectSnapshot.runs || []);
    const scope = focusRun?.status === "failed" || runDisplayStatus(focusRun || {}) === "awaiting_approval" || runDisplayStatus(focusRun || {}) === "awaiting_execution"
      ? "rewrite_intervention"
      : "chapter_planning";
    createConversationThread(scope).catch((error) => setStatus(String(error.message || error), "error"));
  });
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
