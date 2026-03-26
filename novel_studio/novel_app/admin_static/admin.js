const state = {
  projects: [],
  selectedProjectId: null,
  selectedRunId: null,
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
  selectedRunLabel: document.getElementById("selected-run-label"),
  statusPill: document.getElementById("status-pill"),
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
        <div class="meta">${project.project_id}</div>
      </button>`;
    })
    .join("");
  el.projectsList.querySelectorAll("[data-project-id]").forEach((node) => {
    node.addEventListener("click", () => selectProject(node.dataset.projectId));
  });
}

function renderChapters(chapters) {
  el.chaptersList.innerHTML = chapters.length
    ? chapters.map((item) => card(`第 ${item.chapter_no} 章`, `${item.title}<br>${item.status}`)).join("")
    : `<div class="empty">暂无章节</div>`;
}

function renderRuns(runs) {
  el.runsList.innerHTML = runs.length
    ? runs
        .map((item) =>
          card(
            item.run_id,
            `${item.status}<br>${item.created_at}`,
            [{ action: "view-run", id: item.run_id, label: "查看工件" }]
          )
        )
        .join("")
    : `<div class="empty">暂无 Run</div>`;
  el.runsList.querySelectorAll("[data-action='view-run']").forEach((node) => {
    node.addEventListener("click", () => loadArtifacts(node.dataset.id));
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
            item.requested_action,
            `${item.status}<br>${item.reason}`,
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
  el.artifactsList.innerHTML = items.length
    ? items
        .map((item) => card(item.artifact_type, item.created_at, [], `<pre>${JSON.stringify(item.payload, null, 2)}</pre>`))
        .join("")
    : `<div class="empty">暂无工件</div>`;
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
  state.projects = await api("/api/projects");
  renderProjects();
  setStatus("项目已更新");
  if (!state.selectedProjectId && state.projects.length) {
    await selectProject(state.projects[0].project_id);
  }
}

async function selectProject(projectId) {
  state.selectedProjectId = projectId;
  renderProjects();
  const project = state.projects.find((item) => item.project_id === projectId);
  el.projectTitle.textContent = project?.name || "未选择项目";
  el.projectMeta.textContent = project ? `${project.project_id}` : "选择左侧项目后查看详情";
  el.createRun.disabled = !project;
  if (!project) return;

  const [chapters, runs, approvals] = await Promise.all([
    api(`/api/projects/${projectId}/chapters`),
    api(`/api/projects/${projectId}/runs`),
    api(`/api/projects/${projectId}/approval-requests`),
  ]);
  renderChapters(chapters);
  renderRuns(runs);
  renderApprovals(approvals);
}

async function loadArtifacts(runId) {
  state.selectedRunId = runId;
  el.selectedRunLabel.textContent = runId;
  const artifacts = await api(`/api/runs/${runId}/artifacts`);
  renderArtifacts(artifacts);
}

async function loadAudit() {
  const logs = await api("/api/audit-logs?limit=20");
  renderAudit(logs);
}

async function waitForRunCompletion(runId, timeoutMs = 480000) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    const run = await api(`/api/runs/${runId}`);
    const progress = run.result?.progress || {};
    if (run.status === "running") {
      const marker = progress.latest_event || progress.current_node || "starting";
      setStatus(`Run 执行中: ${marker}`, "warn");
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
      setStatus("续写任务已提交，正在后台执行…", "warn");
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
    await api("/api/projects", {
      method: "POST",
      body: JSON.stringify({
        name: formData.get("name"),
        description: formData.get("description") || null,
        default_target_chapters: Number(formData.get("default_target_chapters") || 1),
        default_user_brief: JSON.parse(String(formData.get("default_user_brief") || "{}")),
      }),
    });
    form.reset();
    await loadProjects();
    await loadAudit();
    setStatus("项目已创建");
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
    setStatus("Run 已提交，正在后台执行…", "warn");
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
