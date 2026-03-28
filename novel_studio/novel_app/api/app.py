from __future__ import annotations
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from pathlib import Path
from threading import Thread

from fastapi import Body, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from novel_app.api.schemas import (
    ApiErrorResponse,
    ApprovalExecuteRequest,
    ApprovalExecuteResponse,
    ApprovalRequestCreateRequest,
    ApprovalRequestResponse,
    ApprovalResolveRequest,
    ArtifactResponse,
    AuditLogResponse,
    ChapterResponse,
    ConversationMessageCreateRequest,
    ConversationMessageResponse,
    ConversationDecisionCreateRequest,
    ConversationDecisionDirectCreateRequest,
    ConversationDecisionUpdateRequest,
    ConversationDecisionResponse,
    ConversationThreadCreateRequest,
    ConversationThreadResponse,
    HealthResponse,
    ProjectCreateRequest,
    ProjectResponse,
    RunCreateRequest,
    RunResponse,
)
from novel_app.config import AppConfig, load_config
from novel_app.services.store import InMemoryStore
from novel_app.services.sql_store import SqlAlchemyStore
from novel_app.services.workflow import WorkflowService
from novel_app.services.store import utc_now_iso


LIVE_ARTIFACT_TYPES = [
    "creative_contract",
    "story_bible",
    "arc_plan",
    "planning_context",
    "current_card",
    "drafting_context",
    "current_draft",
    "phase_decision",
    "publish_package",
    "canon_state",
    "feedback_summary",
    "chapter_lesson",
    "writer_playbook",
    "issue_ledger",
    "review_resolution_trace",
    "latest_review_reports",
    "human_guidance",
    "human_checkpoint",
    "blockers",
    "event_log",
]
RUN_STALE_TIMEOUT_SECONDS = 900
REVIEWER_STALL_HINT_SECONDS = 180
REVIEWER_NODE_TO_REPORTER = {
    "continuity_reviewer": "continuity",
    "pacing_reviewer": "pacing",
    "style_reviewer": "style",
    "reader_simulator": "reader_sim",
}
REVIEWER_REPORTER_TO_NODE = {value: key for key, value in REVIEWER_NODE_TO_REPORTER.items()}


def run_requires_human_approval(result: dict[str, object]) -> bool:
    phase_decision = result.get("phase_decision") or {}
    blockers = result.get("blockers") or []
    return bool(blockers) or phase_decision.get("final_decision") == "human_check"


def suggested_recovery_mode(
    *,
    human_guidance: dict[str, object] | None = None,
    requested_action: str | None = None,
) -> str:
    if requested_action in {"continue", "rewrite", "replan"}:
        return requested_action
    guidance = human_guidance or {}
    suggested_actions = " ".join(str(item) for item in (guidance.get("suggested_actions") or []))
    if "章卡" in suggested_actions or "重做章卡" in suggested_actions or "重规划" in suggested_actions:
        return "replan"
    if guidance.get("must_fix") or guidance.get("stubborn_issues"):
        return "rewrite"
    return "continue"


def infer_run_chapter(run) -> int | None:
    result = run.result or {}
    progress = result.get("progress") or {}
    publish_package = result.get("publish_package") or {}
    current_card = result.get("current_card") or {}
    feedback_summary = result.get("feedback_summary") or {}
    for candidate in (
        progress.get("chapter_no"),
        publish_package.get("chapter_no"),
        current_card.get("chapter_no"),
        feedback_summary.get("chapter_no"),
        run.request.get("target_chapters"),
    ):
        try:
            if candidate is not None:
                return int(candidate)
        except (TypeError, ValueError):
            continue
    return None


def create_app(
    *,
    config: AppConfig | None = None,
    store: InMemoryStore | None = None,
) -> FastAPI:
    static_dir = Path(__file__).resolve().parents[1] / "admin_static"
    app = FastAPI(
        title="NovelStudio API",
        version="0.1.0",
        responses={
            400: {"model": ApiErrorResponse},
            404: {"model": ApiErrorResponse},
            500: {"model": ApiErrorResponse},
        },
    )
    app.state.config = config or load_config()
    app.state.store = store or SqlAlchemyStore(app.state.config.database_url)
    if hasattr(app.state.store, "create_tables"):
        app.state.store.create_tables()
    app.state.workflow = WorkflowService(app.state.config)
    app.mount("/admin-static", StaticFiles(directory=static_dir), name="admin-static")

    def infer_stage_goal(*, current_node: str | None, phase_decision: str | None, chapter_no: int | None) -> str:
        if phase_decision == "replan":
            return f"重新规划第 {chapter_no or 1} 章章卡。"
        mapping = {
            "interviewer_contract": "整理创作约束与小说契约。",
            "lore_builder": "生成故事设定与世界观骨架。",
            "arc_planner": "规划主线卷纲与阶段目标。",
            "chapter_planner": f"生成第 {chapter_no or 1} 章章卡。",
            "draft_writer": f"撰写第 {chapter_no or 1} 章初稿。",
            "patch_writer": f"修补第 {chapter_no or 1} 章稿件。",
            "continuity_reviewer": "检查连续性与设定一致性。",
            "pacing_reviewer": "检查节奏与推进速度。",
            "style_reviewer": "检查文风和可读性。",
            "reader_simulator": "模拟读者感受与追读欲望。",
            "chief_editor": "汇总审校意见并决定下一步。",
            "release_prepare": "整理发布包与对外可读内容。",
            "canon_commit": "回写 Canon 与连载状态。",
            "feedback_ingest": "落库反馈与章节完成状态。",
            "human_gate": "等待人工处理。",
        }
        return mapping.get(current_node, "等待下一步节点执行。")

    def infer_possible_cause(*, current_node: str | None, phase_decision: str | None) -> str | None:
        if current_node in {"chapter_planner", "draft_writer", "patch_writer"}:
            return "当前节点依赖外部模型生成，长时间无更新通常意味着上游请求过慢或挂起。"
        if current_node in {"continuity_reviewer", "pacing_reviewer", "style_reviewer", "reader_simulator"}:
            return "当前节点依赖外部模型审校，长时间无更新通常意味着审校请求没有返回。"
        if current_node == "chief_editor" and phase_decision == "replan":
            return "系统已判定需要重规划；如果后续长时间无更新，通常是重新生成章卡的模型调用挂住。"
        return None

    def reviewer_timeout_reason(review_progress: dict[str, object] | None, *, include_duration: bool) -> str | None:
        progress = review_progress or {}
        reviewer = progress.get("longest_wait_reviewer")
        seconds = int(progress.get("longest_wait_seconds", 0) or 0)
        if not reviewer or seconds <= 0:
            return None
        label = REVIEWER_NODE_TO_REPORTER.get(str(reviewer), str(reviewer))
        label = {
            "continuity": "连续性审校",
            "pacing": "节奏审校",
            "style": "文风审校",
            "reader_sim": "读者模拟",
        }.get(label, str(reviewer))
        if include_duration:
            return f"最可能卡在 {label}，已等待约 {seconds // 60} 分钟。"
        return f"当前最可能卡在 {label}。"

    def build_live_artifacts(state: dict[str, object]) -> list[dict[str, object]]:
        artifacts: list[dict[str, object]] = []
        for artifact_type in LIVE_ARTIFACT_TYPES:
            payload = state.get(artifact_type)
            if payload is None:
                continue
            artifacts.append(
                {
                    "artifact_type": artifact_type,
                    "payload": payload,
                }
            )
        return artifacts

    def build_manual_failure_result(run, *, reason: str, operator_id: str) -> dict[str, object]:
        result = dict(run.result or {})
        progress = dict(result.get("progress") or {})
        event_log_tail = list(progress.get("event_log_tail") or [])
        event_log_tail.append("manual_fail")
        result["progress"] = {
            **progress,
            "latest_event": "manual_fail",
            "event_log_tail": event_log_tail[-5:],
            "updated_at": utc_now_iso(),
            "possible_cause": reason,
        }
        result["manual_intervention"] = {
            "action": "mark_failed",
            "operator_id": operator_id,
            "reason": reason,
            "at": utc_now_iso(),
        }
        return result

    def parse_timestamp(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    def build_stale_failure_result(run, *, stale_seconds: int) -> dict[str, object]:
        result = dict(run.result or {})
        progress = dict(result.get("progress") or {})
        event_log_tail = list(progress.get("event_log_tail") or [])
        event_log_tail.append("auto_timeout")
        reason = f"系统自动判定该运行已超时：连续 {stale_seconds // 60} 分钟没有新进度。"
        reviewer_reason = reviewer_timeout_reason(progress.get("review_progress"), include_duration=True)
        if reviewer_reason:
            reason = f"{reason} {reviewer_reason}"
        result["progress"] = {
            **progress,
            "latest_event": "auto_timeout",
            "event_log_tail": event_log_tail[-5:],
            "updated_at": utc_now_iso(),
            "possible_cause": reason,
            "stage_goal": progress.get("stage_goal") or "当前运行已被自动收口，请决定是否重试。",
            "stalled_for_seconds": stale_seconds,
        }
        result["manual_intervention"] = {
            "action": "auto_timeout",
            "operator_id": "system",
            "reason": reason,
            "at": utc_now_iso(),
        }
        return result

    def initial_progress_snapshot(*, current_node: str) -> dict[str, object]:
        return {
            "progress": {
                "current_node": current_node,
                "latest_event": "run_started",
                "event_log_tail": [],
                "chapter_no": None,
                "rewrite_count": 0,
                "phase_decision": None,
                "updated_at": utc_now_iso(),
                "stage_goal": infer_stage_goal(current_node=current_node, phase_decision=None, chapter_no=None),
                "possible_cause": None,
                "review_progress": {
                    "stage_status": "not_started",
                    "stage_started_at": None,
                    "completed_count": 0,
                    "total_count": len(REVIEWER_NODE_TO_REPORTER),
                    "active_reviewers": [],
                    "pending_reviewers": list(REVIEWER_NODE_TO_REPORTER.values()),
                    "longest_wait_reviewer": None,
                    "longest_wait_seconds": 0,
                    "stall_hint": None,
                    "reviewers": {},
                },
            }
        }

    def build_review_progress(*, tracker: dict[str, object], current_node: str | None, state: dict[str, object]) -> dict[str, object]:
        reviewers = {
            reviewer: dict((tracker.get("reviewers") or {}).get(reviewer) or {})
            for reviewer in REVIEWER_NODE_TO_REPORTER.values()
        }
        timestamp = utc_now_iso()
        stage_started_at = tracker.get("stage_started_at")
        if current_node in {"draft_writer", "patch_writer"}:
            stage_started_at = timestamp
            reviewers = {
                reviewer: {
                    "status": "running",
                    "started_at": stage_started_at,
                    "finished_at": None,
                    "decision": None,
                    "total_score": None,
                }
                for reviewer in REVIEWER_NODE_TO_REPORTER.values()
            }

        latest_reports = {
            str(report.get("reviewer", "")).strip(): report
            for report in (state.get("review_reports") or [])
            if str(report.get("reviewer", "")).strip()
        }
        if current_node in REVIEWER_NODE_TO_REPORTER:
            if not stage_started_at:
                stage_started_at = timestamp
            just_finished = REVIEWER_NODE_TO_REPORTER[current_node]
            for reviewer in REVIEWER_NODE_TO_REPORTER.values():
                existing = reviewers.get(reviewer) or {}
                if not existing.get("started_at"):
                    existing["started_at"] = stage_started_at
                if reviewer == just_finished:
                    report = latest_reports.get(reviewer, {})
                    existing.update(
                        {
                            "status": "completed",
                            "finished_at": timestamp,
                            "decision": report.get("decision"),
                            "total_score": (report.get("scores") or {}).get("total"),
                        }
                    )
                elif existing.get("status") != "completed":
                    existing["status"] = "running"
                reviewers[reviewer] = existing

        if current_node == "chief_editor" and latest_reports:
            if not stage_started_at:
                stage_started_at = timestamp
            for reviewer, report in latest_reports.items():
                existing = reviewers.get(reviewer) or {}
                existing.update(
                    {
                        "status": "completed",
                        "started_at": existing.get("started_at") or stage_started_at,
                        "finished_at": existing.get("finished_at") or timestamp,
                        "decision": report.get("decision"),
                        "total_score": (report.get("scores") or {}).get("total"),
                    }
                )
                reviewers[reviewer] = existing

        completed = [name for name, item in reviewers.items() if item.get("status") == "completed"]
        active = [name for name, item in reviewers.items() if item.get("status") == "running"]
        pending = [name for name, item in reviewers.items() if item.get("status") in {None, "pending"}]
        longest_wait_reviewer = None
        longest_wait_seconds = 0
        for reviewer in active:
            started_at = parse_timestamp((reviewers.get(reviewer) or {}).get("started_at"))
            if started_at is None:
                continue
            waited_seconds = max(0, int((datetime.now(timezone.utc) - started_at).total_seconds()))
            reviewers[reviewer]["stalled_for_seconds"] = waited_seconds
            if waited_seconds >= longest_wait_seconds:
                longest_wait_seconds = waited_seconds
                longest_wait_reviewer = reviewer
        if stage_started_at and not active and not pending:
            stage_status = "completed"
        elif stage_started_at:
            stage_status = "running"
        else:
            stage_status = "not_started"
        tracker["stage_started_at"] = stage_started_at
        tracker["reviewers"] = reviewers
        return {
            "stage_status": stage_status,
            "stage_started_at": stage_started_at,
            "completed_count": len(completed),
            "total_count": len(REVIEWER_NODE_TO_REPORTER),
            "active_reviewers": active,
            "pending_reviewers": pending,
            "longest_wait_reviewer": longest_wait_reviewer,
            "longest_wait_seconds": longest_wait_seconds,
            "stall_hint": reviewer_timeout_reason(
                {
                    "longest_wait_reviewer": longest_wait_reviewer,
                    "longest_wait_seconds": longest_wait_seconds,
                },
                include_duration=False,
            )
            if longest_wait_seconds >= REVIEWER_STALL_HINT_SECONDS
            else None,
            "reviewers": reviewers,
        }

    def build_progress_snapshot(
        *,
        state: dict[str, object],
        current_node: str | None,
        review_progress: dict[str, object] | None = None,
    ) -> dict[str, object]:
        event_log = state.get("event_log") or []
        current_card = state.get("current_card") or {}
        publish_package = state.get("publish_package") or {}
        phase_decision = state.get("phase_decision") or {}
        chapter_no = publish_package.get("chapter_no") or current_card.get("chapter_no")
        final_decision = phase_decision.get("final_decision")
        effective_review_progress = review_progress or {
            "stage_status": "not_started",
            "stage_started_at": None,
            "completed_count": 0,
            "total_count": len(REVIEWER_NODE_TO_REPORTER),
            "active_reviewers": [],
            "pending_reviewers": list(REVIEWER_NODE_TO_REPORTER.values()),
            "longest_wait_reviewer": None,
            "longest_wait_seconds": 0,
            "stall_hint": None,
            "reviewers": {},
        }
        possible_cause = infer_possible_cause(
            current_node=current_node,
            phase_decision=final_decision,
        )
        stall_hint = effective_review_progress.get("stall_hint")
        if stall_hint:
            possible_cause = f"{possible_cause} {stall_hint}" if possible_cause else str(stall_hint)
        return {
            "progress": {
                "current_node": current_node,
                "latest_event": event_log[-1] if event_log else None,
                "event_log_tail": event_log[-5:],
                "chapter_no": chapter_no,
                "rewrite_count": state.get("rewrite_count", 0),
                "phase_decision": final_decision,
                "updated_at": utc_now_iso(),
                "stage_goal": infer_stage_goal(
                    current_node=current_node,
                    phase_decision=final_decision,
                    chapter_no=chapter_no,
                ),
                "possible_cause": possible_cause,
                "review_progress": effective_review_progress,
            },
            "live_artifacts": build_live_artifacts(state),
        }

    def enrich_run_payload(run) -> dict[str, object]:
        payload = dict(run.__dict__)
        result = dict(payload.get("result") or {})
        if run.status == "awaiting_approval":
            approval = next(
                (
                    item
                    for item in app.state.store.list_approval_requests(project_id=run.project_id)
                    if item.run_id == run.run_id
                ),
                None,
            )
            thread = find_conversation_thread(project_id=run.project_id, linked_run_id=run.run_id, scope="rewrite_intervention")
            checkpoint = build_human_checkpoint(run=run, result=result, approval=approval, thread=thread)
            if checkpoint:
                result["human_checkpoint"] = checkpoint
        progress = dict(result.get("progress") or {})
        if progress:
            chapter_no = progress.get("chapter_no")
            phase_decision = progress.get("phase_decision")
            progress.setdefault(
                "stage_goal",
                infer_stage_goal(
                    current_node=progress.get("current_node"),
                    phase_decision=phase_decision,
                    chapter_no=chapter_no,
                ),
            )
            progress.setdefault(
                "possible_cause",
                infer_possible_cause(
                    current_node=progress.get("current_node"),
                    phase_decision=phase_decision,
                ),
            )
            updated_at = parse_timestamp(progress.get("updated_at")) or parse_timestamp(run.created_at)
            if updated_at is not None:
                progress["stalled_for_seconds"] = max(
                    0,
                    int((datetime.now(timezone.utc) - updated_at).total_seconds()),
                )
            result["progress"] = progress
            payload["result"] = result
        stored_artifacts = app.state.store.list_artifacts(run.run_id)
        artifact_count = len(stored_artifacts)
        if run.status == "running":
            live_artifacts = (result.get("live_artifacts") or []) if isinstance(result, dict) else []
            if live_artifacts:
                seen_types = {item.artifact_type for item in stored_artifacts}
                artifact_count += sum(
                    1
                    for item in live_artifacts
                    if item.get("artifact_type") and item.get("artifact_type") not in seen_types
                )
        payload["artifact_count"] = artifact_count
        payload["has_artifacts"] = artifact_count > 0
        payload["result"] = result
        return payload

    def maybe_finalize_stale_run(run):
        if run.status != "running":
            return run
        progress = (run.result or {}).get("progress") or {}
        last_activity = parse_timestamp(progress.get("updated_at")) or parse_timestamp(run.created_at)
        if last_activity is None:
            return run
        stale_seconds = int((datetime.now(timezone.utc) - last_activity).total_seconds())
        if stale_seconds < RUN_STALE_TIMEOUT_SECONDS:
            return run
        reason = f"系统自动判定该运行已超时：连续 {stale_seconds // 60} 分钟没有新进度。"
        reviewer_reason = reviewer_timeout_reason(progress.get("review_progress"), include_duration=True)
        if reviewer_reason:
            reason = f"{reason} {reviewer_reason}"
        updated_run = app.state.store.update_run(
            run_id=run.run_id,
            status="failed",
            result=build_stale_failure_result(run, stale_seconds=stale_seconds),
            error=reason,
            only_if_status_in={"running"},
        )
        return updated_run or app.state.store.get_run(run.run_id) or run

    def finalize_run_success(*, run_id: str, result: dict[str, object]) -> None:
        existing_run = app.state.store.get_run(run_id)
        if not existing_run:
            return
        run_status = "awaiting_approval" if run_requires_human_approval(result) else "completed"
        approval = None
        intervention_thread = None
        if run_status == "awaiting_approval":
            phase_reason = ((result.get("phase_decision") or {}).get("reason")) or "需要人工确认后继续执行"
            chapter_no = infer_run_chapter(existing_run)
            approval = app.state.store.create_approval_request(
                project_id=existing_run.project_id,
                run_id=existing_run.run_id,
                chapter_no=chapter_no,
                requested_action="continue",
                reason="；".join(result.get("blockers") or []) if (result.get("blockers") or []) else str(phase_reason),
                payload={"source": "auto"},
            )
            project = app.state.store.get_project(existing_run.project_id)
            if project is not None:
                intervention_thread = ensure_intervention_thread(
                    project=project,
                    run_id=existing_run.run_id,
                    chapter_no=chapter_no,
                )
            checkpoint = build_human_checkpoint(
                run=existing_run,
                result=result,
                approval=approval,
                thread=intervention_thread,
            )
            if checkpoint:
                result = {**result, "human_checkpoint": checkpoint}
        updated_run = app.state.store.update_run(
            run_id=run_id,
            status=run_status,
            result=result,
            error=None,
            only_if_status_in={"running"},
        )
        if not updated_run:
            return
        app.state.store.save_run_outputs(run=updated_run, result=result)

    def finalize_run_failure(*, run_id: str, error: Exception) -> None:
        app.state.store.update_run(
            run_id=run_id,
            status="failed",
            result=None,
            error=str(error),
            only_if_status_in={"running"},
        )

    def launch_background_run(*, run_id: str, work) -> None:
        progress_tracker: dict[str, object] = {
            "stage_started_at": None,
            "reviewers": {},
        }

        def on_update(current_node: str | None, state: dict[str, object]) -> None:
            review_progress = build_review_progress(tracker=progress_tracker, current_node=current_node, state=state)
            app.state.store.update_run(
                run_id=run_id,
                status="running",
                result=build_progress_snapshot(
                    state=state,
                    current_node=current_node,
                    review_progress=review_progress,
                ),
                error=None,
                only_if_status_in={"running"},
            )

        def runner() -> None:
            try:
                result = work(on_update)
                finalize_run_success(run_id=run_id, result=result)
            except Exception as exc:
                finalize_run_failure(run_id=run_id, error=exc)

        Thread(target=runner, daemon=True).start()

    @app.middleware("http")
    async def attach_request_id(request: Request, call_next):
        request_id = request.headers.get("x-request-id", f"req_{uuid4().hex[:12]}")
        request.state.request_id = request_id
        request.state.actor = request.headers.get("x-operator-id", app.state.config.operator_id)
        if request.url.path.startswith("/api") and app.state.config.admin_token:
            provided = request.headers.get("x-api-key")
            auth_header = request.headers.get("authorization", "")
            if auth_header.lower().startswith("bearer "):
                provided = auth_header[7:].strip()
            if provided != app.state.config.admin_token:
                return JSONResponse(status_code=401, content={"detail": "unauthorized"})
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response

    def audit(
        *,
        request: Request,
        response: Response,
        status_code: int,
        action: str,
        resource_type: str,
        resource_id: str | None,
        project_id: str | None,
        run_id: str | None,
        approval_id: str | None,
        payload: dict,
    ) -> None:
        app.state.store.create_audit_log(
            project_id=project_id,
            run_id=run_id,
            approval_id=approval_id,
            actor=request.state.actor,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            request_id=request.state.request_id,
            path=request.url.path,
            method=request.method,
            status_code=status_code,
            payload=payload,
        )

    def conversation_title(*, scope: str, chapter_no: int | None) -> str:
        if scope == "project_bootstrap":
            return "立项共创"
        if scope == "character_room":
            return "人物讨论"
        if scope == "outline_room":
            return "大纲讨论"
        if scope == "chapter_planning":
            return f"第 {chapter_no or '?'} 章章卡协商"
        if scope == "rewrite_intervention":
            return f"第 {chapter_no or '?'} 章修稿协作"
        if scope == "chapter_retro":
            return f"第 {chapter_no or '?'} 章复盘"
        return "创作对话"

    def interview_blueprint(scope: str) -> dict | None:
        if scope == "project_bootstrap":
            return {
                "goal": "先接住模糊灵感，再把项目方向逐步问清楚，形成可执行的立项基础。",
                "decision_types": ["writer_playbook_rule", "character_note", "outline_constraint"],
                "topics": [
                    {
                        "title": "最想保住的吸引力",
                        "prompt": "先别急着定义卖点。你现在最想保住的，是下面哪种吸引力？也可以自己补一句。",
                        "options": ["爽感往上冲", "情绪拉扯", "悬念感", "人物关系", "我还说不清"],
                        "extra_options": ["压迫中翻盘", "谜团驱动", "宿命对抗", "反差感"],
                        "rephrase_prompt": "换个问法：如果只保住一种读者体验，你最怕它最后丢掉什么？",
                        "support_prompt": "没关系，我们先不要定义专业术语。你可以直接选一个最接近的方向，或者说“更像 A 但又有一点 B”。",
                        "answer_mode": "choice_or_short_text",
                    },
                    {
                        "title": "主角行动方式",
                        "prompt": "如果主角一出场就要让人记住，你更想让他像哪一类人？",
                        "options": ["主动争", "被迫卷入", "隐忍反击", "外冷内烈", "我还没想清"],
                        "extra_options": ["嘴硬手快", "克制但危险", "看似被动实则有盘算", "先忍后爆"],
                        "rephrase_prompt": "换个问法：这个主角第一次出手时，你更希望读者觉得他是“马上会动的人”，还是“被逼急才动的人”？",
                        "support_prompt": "你也可以只说一句感觉，比如“克制但不能太软”“不想写成纯莽夫”。",
                        "answer_mode": "choice_or_short_text",
                    },
                    {
                        "title": "故事推进方式",
                        "prompt": "这本书往前推时，你更希望主要靠什么力量？",
                        "options": ["升级推进", "阴谋推进", "关系推进", "生存推进", "混合推进"],
                        "extra_options": ["先升级后揭谜", "先压迫后翻盘", "主打关系拉扯", "任务链推进"],
                        "rephrase_prompt": "换个问法：如果读者一口气追十章，他主要会因为哪种东西舍不得停下来？",
                        "support_prompt": "不用精确定义结构，你只要说“更像靠阴谋吊着往下看”这种程度也可以。",
                        "answer_mode": "choice_or_short_text",
                    },
                    {
                        "title": "不能写歪的边界",
                        "prompt": "最后再补一个边界：这本书最不能写歪的地方是什么？也可以直接说你明确不接受什么。",
                        "options": ["不要套路化打脸", "不要无代价外挂", "不要人物性格突然变形", "不要文风油腻", "先跳过这个问题"],
                        "extra_options": ["不要后宫泛滥", "不要一味卖惨", "不要主角降智", "不要反派太工具人"],
                        "rephrase_prompt": "换个问法：如果后面写着写着跑偏了，你最容易第一时间喊停的会是什么？",
                        "support_prompt": "如果暂时说不清，也可以先跳过，后面写出几章后再补边界。",
                        "answer_mode": "short_text_with_choices",
                    },
                ],
                "closing_prompt": "这几项已经足够形成第一版立项草案。下一步建议先把稳定结论采纳为人物设定、卷纲约束或长期规则，再继续细化。",
            }
        if scope == "character_room":
            return {
                "goal": "把人物感觉逐步收紧成稳定的人物设定，而不是一开始就逼出完整小传。",
                "decision_types": ["character_note"],
                "topics": [
                    {
                        "title": "主角第一印象",
                        "prompt": "如果只用一个感觉描述主角，你更希望他给人的第一印象是下面哪种？",
                        "options": ["克制", "危险", "倔强", "聪明", "讨喜", "还没想清"],
                        "extra_options": ["沉默但压迫感强", "看着冷其实很护短", "嘴上淡但下手果断", "不讨喜但很上头"],
                        "rephrase_prompt": "换个问法：主角第一次出场时，你更希望读者先喜欢他、先怕他，还是先想看懂他？",
                        "support_prompt": "你可以只说一种感觉，比如“别太少年气”“要有压迫感但不能油”。",
                        "answer_mode": "choice_or_short_text",
                    },
                    {
                        "title": "主角真正想摆脱什么",
                        "prompt": "主角最想摆脱的是什么？可以是处境、关系、身份、命运，或别的东西。",
                        "options": ["弱小处境", "被控制的人生", "错误身份", "失败命运", "我想自己补充"],
                        "extra_options": ["羞辱与轻视", "负债或罪名", "家族/宗门束缚", "被当工具使用"],
                        "rephrase_prompt": "换个问法：主角最受不了现在的哪一点？只要说最刺他的那件事就行。",
                        "support_prompt": "如果你只知道他“不甘心”，也可以先围绕不甘心补一句最具体的来源。",
                        "answer_mode": "choice_or_short_text",
                    },
                    {
                        "title": "关键关系张力",
                        "prompt": "最关键的关系张力更像哪一种？",
                        "options": ["师徒/前辈压迫", "宿敌对抗", "同伴互相拉扯", "亲密关系试探", "我自己描述"],
                        "extra_options": ["旧恩旧怨", "利益绑定但互不信任", "强者压迫弱者反抗", "表面合作暗中试探"],
                        "rephrase_prompt": "换个问法：这本书里最容易写出火花的两个人，为什么一见面就不可能轻松？",
                        "support_prompt": "你也可以先说“我最想写的是某两个人之间那种既靠近又提防的感觉”。",
                        "answer_mode": "choice_or_short_text",
                    },
                    {
                        "title": "角色边界",
                        "prompt": "什么行为一旦出现，你会立刻觉得这个主角写崩了？",
                        "options": ["突然圣母", "突然莽撞", "突然油腻", "突然降智", "我自己描述"],
                        "extra_options": ["突然恋爱脑", "突然软弱到失真", "突然嘴炮太多", "突然轻佻没分寸"],
                        "rephrase_prompt": "换个问法：读者后面看到哪种变化，会觉得“这已经不是开头那个主角了”？",
                        "support_prompt": "如果不好概括，也可以直接说“不要把他写成……”。",
                        "answer_mode": "choice_or_short_text",
                    },
                ],
                "closing_prompt": "人物核心边界已经基本清楚。下一步建议把关键结论采纳为人物设定，进入后续写作。",
            }
        if scope == "outline_room":
            return {
                "goal": "把第一卷怎么往前推逐步聊清楚，收紧成可执行的大纲约束。",
                "decision_types": ["outline_constraint"],
                "topics": [
                    {
                        "title": "第一卷主推动力",
                        "prompt": "第一卷最主要靠什么把读者往下带？",
                        "options": ["一层层升级", "阴谋逐步揭开", "人物关系变化", "逃生与生存压力", "混合推进"],
                        "extra_options": ["副本/任务推进", "追查真相推进", "身份变化推进", "权力斗争推进"],
                        "rephrase_prompt": "换个问法：如果读者一口气追第一卷，他最可能是被什么持续吊着走？",
                        "support_prompt": "不必一次说全，你只要先选“更像升级线”还是“更像阴谋线”就够了。",
                        "answer_mode": "choice_or_short_text",
                    },
                    {
                        "title": "升级路径",
                        "prompt": "主角在第一卷里更像怎样逼近目标？",
                        "options": ["一次次小胜推进", "先被压制再反打", "边查真相边成长", "靠关系变化推进", "我自己描述"],
                        "extra_options": ["先活下来再翻盘", "先学规则再破规则", "先进入核心圈层", "先失去再争回来"],
                        "rephrase_prompt": "换个问法：第一卷里主角靠什么一步步走到更高的位置？",
                        "support_prompt": "你也可以先说节奏感觉，比如“前期多吃亏，中段才开始反打”。",
                        "answer_mode": "choice_or_short_text",
                    },
                    {
                        "title": "阶段反转",
                        "prompt": "第一卷中段最值得期待的变化更像什么？",
                        "options": ["身份反转", "阵营反转", "认知反转", "力量反转", "我自己描述"],
                        "extra_options": ["信任关系翻车", "主角发现自己被利用", "敌我判断被颠覆", "看似赢其实更危险"],
                        "rephrase_prompt": "换个问法：第一卷中段最该让读者“啊？原来是这样”的那一下，应该落在哪？",
                        "support_prompt": "如果你只知道“中段必须来一个大变化”，也可以先说变化影响的是人、局势还是真相。",
                        "answer_mode": "choice_or_short_text",
                    },
                    {
                        "title": "卷末高潮",
                        "prompt": "卷末最该兑现给读者的感觉是什么？",
                        "options": ["爽到扬眉吐气", "真相揭开一角", "关系彻底翻转", "危险升级忍不住追更", "我自己描述"],
                        "extra_options": ["先赢一场大的", "先揭开一个最大的秘密", "先让主角完成一次身份跃迁", "先把代价打满"],
                        "rephrase_prompt": "换个问法：第一卷结束时，读者最应该带着什么情绪去追第二卷？",
                        "support_prompt": "如果不好概括，就先说卷末更偏“兑现”还是更偏“吊着继续追”。",
                        "answer_mode": "choice_or_short_text",
                    },
                ],
                "closing_prompt": "第一卷方向已经足够清楚。下一步建议把这些结论采纳为卷纲约束，再驱动章卡和正文。",
            }
        return None

    def detect_interview_helper_action(content: str) -> str | None:
        normalized = " ".join(str(content or "").strip().lower().split())
        if not normalized:
            return None
        if "这版理解基本对" in normalized or "确认这版理解" in normalized or "confirm draft" in normalized:
            return "draft_confirm"
        if "先跳过" in normalized or "skip" in normalized:
            return "skip"
        if "换个问法" in normalized or "换种问法" in normalized or "rephrase" in normalized:
            return "rephrase"
        if "更多选项" in normalized or "更具体的方向" in normalized or "more options" in normalized:
            return "more_options"
        if "我还不确定" in normalized or "没想清" in normalized or "不知道怎么答" in normalized:
            return "unsure"
        return None

    def build_interview_user_payload(*, thread, content: str, operator_id: str) -> dict:
        helper_action = detect_interview_helper_action(content) if interview_blueprint(thread.scope) else None
        progress_effect = "answered"
        if helper_action in {"rephrase", "more_options", "unsure", "draft_confirm"}:
            progress_effect = "helper"
        elif helper_action == "skip":
            progress_effect = "skipped"
        return {
            "operator_id": operator_id,
            "interview_helper_action": helper_action,
            "interview_progress_effect": progress_effect,
        }

    def interview_answer_records(messages: list[object]) -> tuple[list[dict], dict | None]:
        handled: list[dict] = []
        last_helper: dict | None = None
        for item in messages:
            if item.role != "user":
                continue
            payload = item.structured_payload or {}
            effect = payload.get("interview_progress_effect")
            helper_action = payload.get("interview_helper_action")
            if effect in {None, "", "answered"}:
                handled.append({"message": item, "effect": "answered", "helper_action": helper_action})
                last_helper = None
                continue
            if effect == "skipped":
                handled.append({"message": item, "effect": "skipped", "helper_action": helper_action})
                last_helper = None
                continue
            if effect == "helper":
                last_helper = {"message": item, "helper_action": helper_action}
        return handled, last_helper

    def build_interview_draft(*, project, answered_records: list[dict], topics: list[dict]) -> dict | None:
        if len(answered_records) < 2:
            return None
        brief = project.default_user_brief or {}
        title = brief.get("title") or project.name
        sections: list[dict[str, str]] = []
        for index, record in enumerate(answered_records[: min(len(answered_records), len(topics), 4)]):
            if record["effect"] == "skipped":
                continue
            answer = str(record["message"].content or "").strip()
            if not answer:
                continue
            sections.append(
                {
                    "label": topics[index]["title"],
                    "summary": answer[:120],
                }
            )
        if not sections:
            return None
        lead = f"《{title}》目前已经有一版可继续确认的方向草案。"
        if brief.get("idea_seed"):
            lead = f"基于你最初的灵感“{str(brief['idea_seed'])[:32]}...”，《{title}》已经有一版可继续确认的方向草案。"
        return {
            "title": "当前理解草案",
            "lead": lead,
            "sections": sections[:4],
            "recommendation": "如果这版大致对，可以继续补缺口；如果明显不对，就用“换个问法”或直接指出系统理解偏了哪里。",
        }

    def build_stage_confirmation(
        *,
        scope: str,
        project,
        answered_records: list[dict],
        topics: list[dict],
        unresolved_topics: list[str],
        current_draft: dict | None,
        adopted: list[object],
    ) -> dict | None:
        if current_draft is None:
            return None
        confirmed_items: list[dict[str, str]] = []
        for index, record in enumerate(answered_records[: min(len(answered_records), len(topics), 4)]):
            if record["effect"] != "answered":
                continue
            content = str(record["message"].content or "").strip()
            if not content:
                continue
            confirmed_items.append({"label": topics[index]["title"], "summary": content[:120]})
        provisional_items = list(current_draft.get("sections") or [])
        adopted_types = {item.decision_type for item in adopted}
        next_steps: list[dict[str, str | bool]] = []
        if scope == "project_bootstrap":
            next_steps.append(
                {
                    "scope": "character_room",
                    "label": "进入人物讨论",
                    "reason": "把主角气质、关系张力和人物边界继续收紧成人物设定。",
                    "recommended": "character_note" not in adopted_types,
                }
            )
            next_steps.append(
                {
                    "scope": "outline_room",
                    "label": "进入大纲讨论",
                    "reason": "把第一卷靠什么推进、哪里反转、卷末兑现什么进一步说清。",
                    "recommended": "outline_constraint" not in adopted_types,
                }
            )
        project_summary = None
        if scope == "project_bootstrap":
            brief = project.default_user_brief or {}
            summary_items: list[dict[str, str]] = []
            if brief.get("idea_seed"):
                summary_items.append({"label": "原始灵感", "summary": str(brief["idea_seed"])[:140]})
            summary_items.extend(provisional_items[:4])
            readiness = "还需要继续补充 1 到 2 个关键点，再进入正式创作。" if unresolved_topics else "这版已经足够作为第一版项目设定摘要，适合继续进入人物或大纲细化。"
            project_summary = {
                "title": "第一版项目设定摘要",
                "items": summary_items[:5],
                "readiness": readiness,
            }
        stage_stub = SimpleNamespace(thread_id="", scope=scope)
        decision_plan = build_stage_decision_plan(
            thread=stage_stub,
            interview_state={
                "current_draft": current_draft,
                "stage_confirmation": {
                    "provisional_items": provisional_items,
                },
            },
        )
        decision_split_preview = None
        if decision_plan:
            counts = {
                "character_note": len([item for item in decision_plan if item["decision_type"] == "character_note"]),
                "outline_constraint": len([item for item in decision_plan if item["decision_type"] == "outline_constraint"]),
                "writer_playbook_rule": len([item for item in decision_plan if item["decision_type"] == "writer_playbook_rule"]),
            }
            decision_split_preview = {
                "items": decision_plan,
                "counts": counts,
            }
        return {
            "confirmed_items": confirmed_items[:4],
            "provisional_items": provisional_items[:4],
            "open_questions": unresolved_topics[:4],
            "next_steps": next_steps,
            "project_summary": project_summary,
            "decision_split_preview": decision_split_preview,
        }

    def build_project_summary_brief(*, project, thread, interview_state: dict[str, object]) -> dict | None:
        stage_confirmation = interview_state.get("stage_confirmation") or {}
        project_summary = stage_confirmation.get("project_summary")
        if not project_summary:
            return None
        brief = dict(project.default_user_brief or {})
        intent_profile = dict(brief.get("intent_profile") or {})
        field_map = {
            "最想保住的吸引力": "reader_pull",
            "主角行动方式": "protagonist_mode",
            "故事推进方式": "drive_mode",
            "不能写歪的边界": "guardrail",
        }
        for item in list(stage_confirmation.get("confirmed_items") or []) + list(stage_confirmation.get("provisional_items") or []):
            label = str(item.get("label") or "").strip()
            summary = str(item.get("summary") or "").strip()
            if not label or not summary:
                continue
            mapped_field = field_map.get(label)
            if mapped_field and mapped_field not in intent_profile:
                intent_profile[mapped_field] = summary
        merged_summary = {
            **project_summary,
            "confirmed_items": list(stage_confirmation.get("confirmed_items") or [])[:4],
            "provisional_items": list(stage_confirmation.get("provisional_items") or [])[:4],
            "open_questions": list(stage_confirmation.get("open_questions") or [])[:4],
            "source_thread_id": thread.thread_id,
            "source_scope": thread.scope,
        }
        if interview_state.get("current_draft"):
            merged_summary["draft_recap"] = interview_state["current_draft"]
        brief["project_summary"] = merged_summary
        brief["capture_stage"] = "clarified"
        if intent_profile:
            brief["intent_profile"] = intent_profile
        if not brief.get("title"):
            brief["title"] = project.name
        return brief

    def infer_stage_decision_type(label: str) -> str | None:
        normalized = str(label or "").strip()
        if normalized == "主角行动方式":
            return "character_note"
        if normalized == "故事推进方式":
            return "outline_constraint"
        if normalized in {"最想保住的吸引力", "不能写歪的边界"}:
            return "writer_playbook_rule"
        return None

    def build_stage_decision_plan(*, thread, interview_state: dict[str, object]) -> list[dict[str, str]]:
        current_draft = interview_state.get("current_draft") or {}
        sections = list(current_draft.get("sections") or [])
        if not sections:
            stage_confirmation = interview_state.get("stage_confirmation") or {}
            sections = list(stage_confirmation.get("provisional_items") or [])
        plan: list[dict[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for item in sections:
            label = str(item.get("label") or "").strip()
            summary = str(item.get("summary") or "").strip()
            decision_type = infer_stage_decision_type(label)
            if not decision_type or not summary:
                continue
            dedupe_key = (decision_type, summary)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            plan.append(
                {
                    "label": label,
                    "content": summary,
                    "decision_type": decision_type,
                    "source_label": f"阶段确认页 · {label}",
                    "target_scope": (
                        "character_room"
                        if decision_type == "character_note"
                        else "outline_room" if decision_type == "outline_constraint" else "project_bootstrap"
                    ),
                }
            )
        return plan

    def interview_prompt_variants(*, topic: dict, helper_action: str | None) -> tuple[str, list[str]]:
        if helper_action == "rephrase":
            prompt = topic.get("rephrase_prompt") or topic["prompt"]
            options = list(topic.get("options") or [])
            return prompt, options
        if helper_action in {"more_options", "unsure"}:
            prompt = topic.get("support_prompt") or topic["prompt"]
            options = list(topic.get("options") or [])
            for item in topic.get("extra_options") or []:
                if item not in options:
                    options.append(item)
            return prompt, options
        return topic["prompt"], list(topic.get("options") or [])

    def build_interview_state(*, thread, project) -> dict | None:
        blueprint = interview_blueprint(thread.scope)
        if blueprint is None:
            return None
        messages = app.state.store.list_conversation_messages(thread.thread_id)
        topics = blueprint["topics"]
        handled_records, last_helper = interview_answer_records(messages)
        completed_count = min(len(handled_records), len(topics))
        confirmed_topics: list[str] = []
        skipped_topics: list[str] = []
        for index, record in enumerate(handled_records[:completed_count]):
            title = topics[index]["title"]
            if record["effect"] == "skipped":
                skipped_topics.append(title)
            else:
                confirmed_topics.append(title)
        unresolved_topics = [item["title"] for item in topics[completed_count:]]
        next_topic = topics[completed_count] if completed_count < len(topics) else None
        next_prompt = (
            interview_prompt_variants(topic=next_topic, helper_action=last_helper["helper_action"] if last_helper else None)[0]
            if next_topic is not None
            else blueprint["closing_prompt"]
        )
        next_options = (
            interview_prompt_variants(topic=next_topic, helper_action=last_helper["helper_action"] if last_helper else None)[1]
            if next_topic is not None
            else []
        )
        relevant_types = set(blueprint["decision_types"])
        adopted = [
            item
            for item in app.state.store.list_conversation_decisions(
                project_id=thread.project_id,
                thread_id=thread.thread_id,
            )
            if item.decision_type in relevant_types
        ]
        brief = project.default_user_brief or {}
        basis = []
        if brief.get("title"):
            basis.append(f"书名：{brief['title']}")
        if brief.get("genre"):
            basis.append(f"题材：{brief['genre']}")
        if brief.get("idea_seed_type"):
            basis.append(f"灵感类型：{brief['idea_seed_type']}")
        if brief.get("idea_seed"):
            basis.append(f"原始灵感：{str(brief['idea_seed'])[:60]}")
        if brief.get("hook"):
            basis.append(f"当前钩子：{brief['hook']}")
        answered_count = len(confirmed_topics)
        reflection_summary = (
            f"目前已确认 {answered_count} 项：{'、'.join(confirmed_topics)}。"
            if confirmed_topics
            else "当前还在捕获原始意图，系统会继续用小问题帮你把方向问清。"
        )
        if skipped_topics:
            reflection_summary = f"{reflection_summary} 已跳过：{'、'.join(skipped_topics)}。"
        current_draft = build_interview_draft(project=project, answered_records=handled_records, topics=topics)
        stage_confirmation = build_stage_confirmation(
            scope=thread.scope,
            project=project,
            answered_records=handled_records,
            topics=topics,
            unresolved_topics=unresolved_topics,
            current_draft=current_draft,
            adopted=adopted,
        )
        return {
            "goal": blueprint["goal"],
            "completion_count": completed_count,
            "total_topics": len(topics),
            "completion_label": f"{completed_count}/{len(topics)}",
            "confirmed_topics": confirmed_topics,
            "skipped_topics": skipped_topics,
            "unresolved_topics": unresolved_topics,
            "next_topic_title": next_topic["title"] if next_topic else None,
            "next_prompt": next_prompt,
            "next_options": next_options,
            "answer_mode": next_topic.get("answer_mode", "short_text") if next_topic else "review",
            "basis": basis,
            "adopted_count": len(adopted),
            "adopted_highlights": [item.summary for item in adopted[:3]],
            "reflection_summary": reflection_summary,
            "current_draft": current_draft,
            "stage_confirmation": stage_confirmation,
            "last_helper_action": last_helper["helper_action"] if last_helper else None,
        }

    def latest_artifact_payloads(run_id: str) -> dict[str, dict]:
        latest: dict[str, dict] = {}
        for item in app.state.store.list_artifacts(run_id):
            latest[item.artifact_type] = item.payload
        return latest

    def build_thread_context(thread) -> dict | None:
        if thread.scope not in {"chapter_planning", "rewrite_intervention"} or not thread.linked_run_id:
            return None
        run = app.state.store.get_run(thread.linked_run_id)
        if run is None:
            return None
        latest_by_type = latest_artifact_payloads(run.run_id)
        result = run.result or {}
        if thread.scope == "rewrite_intervention":
            human_guidance = result.get("human_guidance") or latest_by_type.get("human_guidance") or {}
            issue_ledger = result.get("issue_ledger") or latest_by_type.get("issue_ledger") or {}
            latest_approval = next(
                (
                    item
                    for item in app.state.store.list_approval_requests(project_id=thread.project_id)
                    if item.run_id == run.run_id
                ),
                None,
            )
            stubborn = [
                issue.get("fix_instruction") or issue.get("evidence") or issue.get("issue_id")
                for issue in (human_guidance.get("stubborn_issues") or [])[:3]
                if issue.get("fix_instruction") or issue.get("evidence") or issue.get("issue_id")
            ]
            must_fix = list(human_guidance.get("must_fix") or [])[:4]
            recovery_mode = suggested_recovery_mode(
                human_guidance=human_guidance,
                requested_action=latest_approval.requested_action if latest_approval else None,
            )
            return {
                "chapter_no": human_guidance.get("chapter_no"),
                "checkpoint_reason": human_guidance.get("reason") or "系统已暂停，等待人工判断。",
                "issue_progress_summary": human_guidance.get("issue_progress_summary") or issue_ledger.get("progress_summary"),
                "must_fix": must_fix,
                "suggested_actions": list(human_guidance.get("suggested_actions") or [])[:3],
                "stubborn_issues": stubborn,
                "approval_id": latest_approval.approval_id if latest_approval else None,
                "approval_status": latest_approval.status if latest_approval else None,
                "recommended_recovery_mode": recovery_mode,
                "recommendation": "先在这条会诊线程里明确保留项，再选择“继续当前流程 / 重做章卡 / 重写正文”中的恢复路径。",
            }
        current_card = result.get("current_card") or latest_by_type.get("current_card") or {}
        planning_context = result.get("planning_context") or latest_by_type.get("planning_context") or {}
        issue_ledger = result.get("issue_ledger") or latest_by_type.get("issue_ledger") or {}
        decisions = [
            item
            for item in app.state.store.list_conversation_decisions(project_id=thread.project_id, thread_id=thread.thread_id)
            if item.decision_type == "chapter_card_patch"
        ]
        patch_highlights = [
            item.payload.get("instruction") or item.payload.get("content") or ""
            for item in decisions[:3]
            if str(item.payload.get("instruction") or item.payload.get("content") or "").strip()
        ]
        pending_issues = [
            item.get("fix_instruction") or item.get("applied_guardrail") or item.get("issue_id")
            for item in (planning_context.get("issue_applications") or [])[:3]
            if item.get("fix_instruction") or item.get("applied_guardrail") or item.get("issue_id")
        ]
        if not pending_issues:
            pending_issues = [
                item.get("fix_instruction") or item.get("evidence") or item.get("issue_id")
                for item in (issue_ledger.get("issues") or [])[:3]
                if item.get("status") in {"open", "recurring"}
            ]
        recommendation = (
            "已形成章卡修订结论，可以带着这些修订开始本章。"
            if patch_highlights
            else "先明确你想改的章卡点，再采纳为章卡修订，然后再开写。"
        )
        return {
            "chapter_no": current_card.get("chapter_no") or thread.linked_chapter_no,
            "purpose": current_card.get("purpose"),
            "pov": current_card.get("pov"),
            "must_include": list(current_card.get("must_include") or [])[:3],
            "must_not_change": list(current_card.get("must_not_change") or [])[:3],
            "guardrails": list(planning_context.get("applied_guardrails") or [])[:4],
            "pending_issues": pending_issues,
            "patch_count": len(decisions),
            "patch_highlights": patch_highlights,
            "recommendation": recommendation,
        }

    def find_conversation_thread(*, project_id: str, linked_run_id: str, scope: str) -> object | None:
        return next(
            (
                item
                for item in app.state.store.list_conversation_threads(project_id)
                if item.scope == scope and item.linked_run_id == linked_run_id and item.status == "open"
            ),
            None,
        )

    def ensure_intervention_thread(*, project, run_id: str, chapter_no: int | None) -> object:
        existing = find_conversation_thread(project_id=project.project_id, linked_run_id=run_id, scope="rewrite_intervention")
        if existing is not None:
            return existing
        thread = app.state.store.create_conversation_thread(
            project_id=project.project_id,
            scope="rewrite_intervention",
            title=conversation_title(scope="rewrite_intervention", chapter_no=chapter_no),
            linked_run_id=run_id,
            linked_chapter_no=chapter_no,
        )
        opening_type, opening_content, opening_payload = build_thread_opening(
            scope="rewrite_intervention",
            project=project,
            run=app.state.store.get_run(run_id),
            chapter_no=chapter_no,
        )
        app.state.store.add_conversation_message(
            thread_id=thread.thread_id,
            role="assistant",
            message_type=opening_type,
            content=opening_content,
            structured_payload=opening_payload,
        )
        app.state.store.add_conversation_message(
            thread_id=thread.thread_id,
            role="system",
            message_type="system_action_result",
            content="系统已在这里为你创建人工检查点。先明确保留项和修改方向，再处理审批或执行续写。",
            structured_payload={
                "source": "auto_checkpoint",
                "run_id": run_id,
                "chapter_no": chapter_no,
            },
        )
        return app.state.store.get_conversation_thread(thread.thread_id) or thread

    def build_human_checkpoint(*, run, result: dict[str, object], approval=None, thread=None) -> dict | None:
        if not run_requires_human_approval(result):
            return None
        human_guidance = result.get("human_guidance") or {}
        issue_ledger = result.get("issue_ledger") or {}
        blockers = result.get("blockers") or []
        recovery_mode = suggested_recovery_mode(
            human_guidance=human_guidance,
            requested_action=approval.requested_action if approval else None,
        )
        return {
            "run_id": run.run_id,
            "chapter_no": infer_run_chapter(run),
            "status": "paused_for_human",
            "reason": human_guidance.get("reason") or "流程已进入人工检查点。",
            "issue_progress_summary": human_guidance.get("issue_progress_summary") or issue_ledger.get("progress_summary"),
            "must_fix": list(human_guidance.get("must_fix") or [])[:4],
            "stubborn_issues": list(human_guidance.get("stubborn_issues") or [])[:3],
            "suggested_actions": list(human_guidance.get("suggested_actions") or [])[:3],
            "blockers": blockers,
            "approval_id": approval.approval_id if approval else None,
            "approval_status": approval.status if approval else None,
            "recommended_recovery_mode": recovery_mode,
            "thread_id": thread.thread_id if thread else None,
            "thread_title": thread.title if thread else None,
        }

    def build_thread_opening(*, scope: str, project, run, chapter_no: int | None) -> tuple[str, str, dict]:
        if scope == "project_bootstrap":
            thread_stub = SimpleNamespace(thread_id="", project_id=project.project_id, scope=scope)
            interview_state = build_interview_state(thread=thread_stub, project=project)
            brief = project.default_user_brief or {}
            title = brief.get("title") or project.name
            seed = str(brief.get("idea_seed") or "").strip()
            content = (
                f"我们先从《{title}》最原始的灵感开始，不要求你现在就回答完整的立项问题。\n\n"
                f"我先接住你现在手里这点材料：{seed or '你还没有写下原始灵感，可以直接用一句话告诉我脑中最清楚的画面、人物、冲突或感觉。'}\n\n"
                f"本线程目标：{interview_state['goal']}\n"
                f"当前进度：{interview_state['completion_label']}\n\n"
                f"先回答第 1 问：{interview_state['next_prompt']}\n"
                f"可直接从这些方向里选：{' / '.join(interview_state['next_options']) if interview_state['next_options'] else '也可以直接用一两句话回答。'}"
            )
            return "assistant_question", content, {"interview_state": interview_state}

        if scope == "character_room":
            thread_stub = SimpleNamespace(thread_id="", project_id=project.project_id, scope=scope)
            interview_state = build_interview_state(thread=thread_stub, project=project)
            brief = project.default_user_brief or {}
            title = brief.get("title") or project.name
            content = (
                f"这是《{title}》的人物讨论线程。\n\n"
                f"本线程目标：{interview_state['goal']}\n"
                f"当前进度：{interview_state['completion_label']}\n\n"
                f"先回答第 1 问：{interview_state['next_prompt']}\n"
                f"可直接选：{' / '.join(interview_state['next_options']) if interview_state['next_options'] else '也可以直接补一句。'}"
            )
            return "assistant_question", content, {"interview_state": interview_state}

        if scope == "outline_room":
            thread_stub = SimpleNamespace(thread_id="", project_id=project.project_id, scope=scope)
            interview_state = build_interview_state(thread=thread_stub, project=project)
            brief = project.default_user_brief or {}
            title = brief.get("title") or project.name
            content = (
                f"这是《{title}》的大纲讨论线程。\n\n"
                f"本线程目标：{interview_state['goal']}\n"
                f"当前进度：{interview_state['completion_label']}\n\n"
                f"先回答第 1 问：{interview_state['next_prompt']}\n"
                f"可直接选：{' / '.join(interview_state['next_options']) if interview_state['next_options'] else '也可以直接补一句。'}"
            )
            return "assistant_question", content, {"interview_state": interview_state}

        if scope == "rewrite_intervention" and run is not None:
            result = run.result or {}
            phase_decision = result.get("phase_decision") or {}
            must_fix = (phase_decision.get("must_fix") or [])[:3]
            issue_ledger = result.get("issue_ledger") or {}
            progress_summary = issue_ledger.get("progress_summary") or "当前还没有结构化的问题账本摘要。"
            content = (
                f"这是第 {chapter_no or '?'} 章的协作修稿线程。\n\n"
                f"当前运行状态：{run.status}\n"
                f"问题账本摘要：{progress_summary}\n"
                f"当前建议优先处理：{'; '.join(must_fix) if must_fix else '先明确这次优先改章卡还是改正文。'}\n\n"
                "请直接告诉我：哪些内容必须保留、这次优先修什么、哪些改法不能接受。\n"
                "等会诊信息明确后，再决定是继续当前流程、重做章卡，还是直接重写正文。"
            )
            return "assistant_diagnosis", content, {"must_fix": must_fix, "progress_summary": progress_summary}

        if scope == "chapter_planning":
            content = (
                f"这是第 {chapter_no or '?'} 章的章卡协商线程。\n\n"
                "建议先确认 3 件事：本章目的、主角动作、章末钩子。"
            )
            return "assistant_question", content, {"suggested_topics": ["本章目的", "主角动作", "章末钩子"]}

        content = (
            f"这是第 {chapter_no or '?'} 章的复盘线程。\n\n"
            "建议先说清楚：这一章为什么算通过、哪些写法值得延续、哪些问题仍要警惕。"
        )
        return "system_summary", content, {"suggested_topics": ["通过原因", "延续规则", "遗留风险"]}

    def build_assistant_followup(*, thread, project, run, user_message: str) -> tuple[str, str, dict]:
        excerpt = user_message.strip().replace("\n", " ")
        if len(excerpt) > 100:
            excerpt = f"{excerpt[:100]}..."
        if thread.scope == "project_bootstrap":
            interview_state = build_interview_state(thread=thread, project=project)
            helper_action = interview_state.get("last_helper_action")
            helper_line = ""
            if helper_action == "rephrase":
                helper_line = "我已经换了一种问法，尽量不用编辑术语。\n"
            elif helper_action == "more_options":
                helper_line = "我给你补了一组更具体的方向，你可以直接挑最接近的一项。\n"
            elif helper_action == "unsure":
                helper_line = "没关系，不确定是正常的。我们先缩小范围，不要求一次说清。\n"
            content = (
                f"已记录你的方向：{excerpt}\n\n"
                f"{helper_line}"
                f"当前采访进度：{interview_state['completion_label']}。\n"
                f"已确认：{'、'.join(interview_state['confirmed_topics']) if interview_state['confirmed_topics'] else '暂未形成稳定结论'}。\n"
                f"当前理解：{interview_state['reflection_summary']}\n"
                f"下一问：{interview_state['next_prompt']}\n"
                f"可直接选：{' / '.join(interview_state['next_options']) if interview_state['next_options'] else '也可以继续自由补充。'}\n"
                f"仍待明确：{'、'.join(interview_state['unresolved_topics']) if interview_state['unresolved_topics'] else '已基本问清，可开始采纳结论。'}"
            )
            payload = {"interview_state": interview_state}
            return "assistant_question", content, payload
        if thread.scope == "character_room":
            interview_state = build_interview_state(thread=thread, project=project)
            helper_action = interview_state.get("last_helper_action")
            helper_line = ""
            if helper_action == "rephrase":
                helper_line = "我已经换了一种问法，尽量先从感觉和边界出发。\n"
            elif helper_action == "more_options":
                helper_line = "我补了一组更具体的人物方向，你可以直接挑最接近的一项。\n"
            elif helper_action == "unsure":
                helper_line = "不用急着写小传，我们先抓住最像的感觉就够了。\n"
            content = (
                f"已记录人物方向：{excerpt}\n\n"
                f"{helper_line}"
                f"当前采访进度：{interview_state['completion_label']}。\n"
                f"已确认：{'、'.join(interview_state['confirmed_topics']) if interview_state['confirmed_topics'] else '暂未形成稳定结论'}。\n"
                f"当前理解：{interview_state['reflection_summary']}\n"
                f"下一问：{interview_state['next_prompt']}\n"
                f"可直接选：{' / '.join(interview_state['next_options']) if interview_state['next_options'] else '也可以继续自由补充。'}\n"
                f"仍待明确：{'、'.join(interview_state['unresolved_topics']) if interview_state['unresolved_topics'] else '已可以采纳为人物设定。'}"
            )
            payload = {"interview_state": interview_state}
            return "assistant_question", content, payload
        if thread.scope == "outline_room":
            interview_state = build_interview_state(thread=thread, project=project)
            helper_action = interview_state.get("last_helper_action")
            helper_line = ""
            if helper_action == "rephrase":
                helper_line = "我已经把问题换成更接近追更体验的问法。\n"
            elif helper_action == "more_options":
                helper_line = "我补了一组更具体的大纲推进方向，你可以先选最接近的一项。\n"
            elif helper_action == "unsure":
                helper_line = "不用一次说清整卷结构，我们先抓住主推动力就行。\n"
            content = (
                f"已记录大纲方向：{excerpt}\n\n"
                f"{helper_line}"
                f"当前采访进度：{interview_state['completion_label']}。\n"
                f"已确认：{'、'.join(interview_state['confirmed_topics']) if interview_state['confirmed_topics'] else '暂未形成稳定结论'}。\n"
                f"当前理解：{interview_state['reflection_summary']}\n"
                f"下一问：{interview_state['next_prompt']}\n"
                f"可直接选：{' / '.join(interview_state['next_options']) if interview_state['next_options'] else '也可以继续自由补充。'}\n"
                f"仍待明确：{'、'.join(interview_state['unresolved_topics']) if interview_state['unresolved_topics'] else '已可以采纳为卷纲约束。'}"
            )
            payload = {"interview_state": interview_state}
            return "assistant_question", content, payload
        if thread.scope == "rewrite_intervention":
            content = (
                f"已记录这次人工意见：{excerpt}\n\n"
                "下一步建议明确三件事：哪些内容必须保留、优先改章卡还是正文、这次必须先关闭哪些旧问题。"
            )
            payload = {"suggested_topics": ["必须保留", "优先修章卡或正文", "必须先关闭的问题"]}
            return "system_summary", content, payload
        if thread.scope == "chapter_planning":
            content = (
                f"已记录本章方向：{excerpt}\n\n"
                "如果你认可当前结论，下一步就可以把它作为章卡修订指令。"
            )
            payload = {"suggested_topics": ["章卡修订指令", "必须兑现", "章末钩子"]}
            return "assistant_proposal", content, payload
        content = (
            f"已记录这次复盘意见：{excerpt}\n\n"
            "下一步可以决定：把哪些内容沉淀为长期写作规则，哪些只保留为本章经验。"
        )
        return "system_summary", content, {"suggested_topics": ["长期规则", "本章经验", "暂不采纳"]}

    def enrich_thread_payload(thread) -> dict:
        payload = dict(thread.__dict__)
        messages = app.state.store.list_conversation_messages(thread.thread_id)
        latest = messages[-1].content if messages else None
        payload["latest_message_preview"] = latest[:120] if latest else None
        payload["message_count"] = len(messages)
        project = app.state.store.get_project(thread.project_id)
        payload["interview_state"] = build_interview_state(thread=thread, project=project) if project else None
        payload["thread_context"] = build_thread_context(thread)
        return payload

    def build_conversation_decision_payload(*, thread, message, decision_type: str) -> dict:
        base = {
            "source": "conversation",
            "thread_id": thread.thread_id,
            "message_id": message.message_id,
            "scope": thread.scope,
            "content": message.content,
        }
        if decision_type == "human_instruction":
            return {
                **base,
                "requested_action": "conversation_guidance",
                "reason": f"来自{thread.title}的人工协作结论",
                "operator_id": None,
                "comment": message.content,
                "payload": {
                    "scope": thread.scope,
                    "linked_run_id": thread.linked_run_id,
                    "linked_chapter_no": thread.linked_chapter_no,
                },
            }
        if decision_type == "writer_playbook_rule":
            return {
                **base,
                "rule": message.content,
            }
        if decision_type == "character_note":
            return {
                **base,
                "note": message.content,
            }
        if decision_type == "outline_constraint":
            return {
                **base,
                "constraint": message.content,
            }
        return {
            **base,
            "instruction": message.content,
            "chapter_no": thread.linked_chapter_no,
        }

    def build_conversation_decision_payload_from_content(
        *,
        thread,
        message_id: str,
        decision_type: str,
        content: str,
        source: str,
        source_label: str | None = None,
    ) -> dict:
        base = {
            "source": source,
            "source_label": source_label,
            "thread_id": thread.thread_id,
            "message_id": message_id,
            "scope": thread.scope,
            "content": content,
        }
        if decision_type == "human_instruction":
            return {
                **base,
                "requested_action": "conversation_guidance",
                "reason": f"来自{thread.title}的结构化协作结论",
                "operator_id": None,
                "comment": content,
                "payload": {
                    "scope": thread.scope,
                    "linked_run_id": thread.linked_run_id,
                    "linked_chapter_no": thread.linked_chapter_no,
                },
            }
        if decision_type == "writer_playbook_rule":
            return {**base, "rule": content}
        if decision_type == "character_note":
            return {**base, "note": content}
        if decision_type == "outline_constraint":
            return {**base, "constraint": content}
        return {**base, "instruction": content, "chapter_no": thread.linked_chapter_no}

    def rewrite_conversation_decision_payload(*, existing_payload: dict, decision_type: str, content: str) -> dict:
        updated = dict(existing_payload or {})
        updated["content"] = content
        if decision_type == "human_instruction":
            updated["comment"] = content
        elif decision_type == "writer_playbook_rule":
            updated["rule"] = content
        elif decision_type == "character_note":
            updated["note"] = content
        elif decision_type == "outline_constraint":
            updated["constraint"] = content
        elif decision_type == "chapter_card_patch":
            updated["instruction"] = content
        return updated

    def merge_conversation_decisions_into_request(*, project_id: str, request_payload: dict[str, object]) -> dict[str, object]:
        decisions = app.state.store.list_conversation_decisions(project_id=project_id)
        if not decisions:
            return request_payload

        updated = dict(request_payload)
        human_guidance = [item for item in decisions if item.decision_type == "human_instruction"]
        playbook_rules = [item.payload.get("rule") for item in decisions if item.decision_type == "writer_playbook_rule"]
        character_notes = [item.payload.get("note") for item in decisions if item.decision_type == "character_note"]
        outline_constraints = [item.payload.get("constraint") for item in decisions if item.decision_type == "outline_constraint"]
        chapter_patches = [item.payload.get("instruction") for item in decisions if item.decision_type == "chapter_card_patch"]
        adopted_decisions = [
            {
                "decision_id": item.decision_id,
                "decision_type": item.decision_type,
                "thread_id": item.thread_id,
                "summary": (
                    item.payload.get("comment")
                    or item.payload.get("rule")
                    or item.payload.get("instruction")
                    or item.payload.get("content")
                    or ""
                ),
            }
            for item in decisions[:8]
        ]

        playbook_rules = [str(item).strip() for item in playbook_rules if str(item or "").strip()]
        character_notes = [str(item).strip() for item in character_notes if str(item or "").strip()]
        outline_constraints = [str(item).strip() for item in outline_constraints if str(item or "").strip()]
        chapter_patches = [str(item).strip() for item in chapter_patches if str(item or "").strip()]
        current_brief = dict(updated.get("user_brief") or {})
        if character_notes:
            merged_character_notes = list(current_brief.get("character_notes") or [])
            for note in character_notes:
                if note not in merged_character_notes:
                    merged_character_notes.append(note)
            current_brief["character_notes"] = merged_character_notes[:12]
        if outline_constraints:
            merged_outline_notes = list(current_brief.get("outline_notes") or [])
            for note in outline_constraints:
                if note not in merged_outline_notes:
                    merged_outline_notes.append(note)
            current_brief["outline_notes"] = merged_outline_notes[:12]
        updated["user_brief"] = current_brief
        updated["conversation_guidance"] = {
            "decision_count": len(decisions),
            "human_instruction_count": len(human_guidance),
            "writer_playbook_rule_count": len(playbook_rules),
            "character_note_count": len(character_notes),
            "outline_constraint_count": len(outline_constraints),
            "chapter_card_patch_count": len(chapter_patches),
            "adopted_decisions": adopted_decisions,
        }
        if playbook_rules:
            current_playbook = dict(updated.get("writer_playbook") or {})
            always_apply = list(current_playbook.get("always_apply") or [])
            for rule in playbook_rules:
                if rule not in always_apply:
                    always_apply.append(rule)
            current_playbook["always_apply"] = always_apply[:16]
            current_playbook.setdefault("version", 1)
            current_playbook.setdefault("validated_patterns", [])
            current_playbook.setdefault("watch_out", [])
            updated["writer_playbook"] = current_playbook

        if human_guidance or chapter_patches:
            current_instruction = dict(updated.get("human_instruction") or {})
            if human_guidance:
                latest = human_guidance[0].payload
                current_instruction.setdefault("requested_action", latest.get("requested_action") or "conversation_guidance")
                current_instruction.setdefault("reason", latest.get("reason") or "来自创作对话的人工结论")
                current_instruction.setdefault("operator_id", latest.get("operator_id"))
                comments = []
                if current_instruction.get("comment"):
                    comments.append(str(current_instruction["comment"]).strip())
                comments.extend(
                    payload.get("comment", "").strip()
                    for payload in [item.payload for item in human_guidance[:3]]
                    if str(payload.get("comment", "")).strip()
                )
                if chapter_patches:
                    comments.extend([f"章卡修订：{item}" for item in chapter_patches[:3]])
                deduped_comments = []
                for item in comments:
                    if item and item not in deduped_comments:
                        deduped_comments.append(item)
                if deduped_comments:
                    current_instruction["comment"] = "\n".join(deduped_comments[:4])
                merged_payload = dict(current_instruction.get("payload") or {})
                merged_payload["conversation_guidance"] = {
                    "human_instruction_count": len(human_guidance),
                    "writer_playbook_rule_count": len(playbook_rules),
                    "character_note_count": len(character_notes),
                    "outline_constraint_count": len(outline_constraints),
                    "chapter_card_patch_count": len(chapter_patches),
                    "latest_thread_id": human_guidance[0].thread_id,
                }
                current_instruction["payload"] = merged_payload
            elif chapter_patches:
                current_instruction.setdefault("requested_action", "chapter_card_patch")
                current_instruction.setdefault("reason", "来自创作对话的章卡修订结论")
                current_instruction["comment"] = "\n".join([f"章卡修订：{item}" for item in chapter_patches[:4]])
                current_instruction["payload"] = {
                    **dict(current_instruction.get("payload") or {}),
                    "conversation_guidance": {
                        "writer_playbook_rule_count": len(playbook_rules),
                        "character_note_count": len(character_notes),
                        "outline_constraint_count": len(outline_constraints),
                        "chapter_card_patch_count": len(chapter_patches),
                    },
                }
            updated["human_instruction"] = current_instruction
        return updated

    @app.exception_handler(ValueError)
    async def value_error_handler(_: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(Exception)
    async def unexpected_error_handler(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=500, content={"detail": f"internal_error: {exc}"})

    @app.get("/healthz", response_model=HealthResponse)
    async def healthz() -> HealthResponse:
        config_value = app.state.config
        database = {"status": "unknown", "backend": "unknown", "detail": None}
        if hasattr(app.state.store, "health_status"):
            database = app.state.store.health_status()
        return HealthResponse(
            status="ok" if database["status"] == "ready" else "degraded",
            stub_mode=config_value.stub_mode,
            model_name=config_value.model_name,
            auth_mode="token" if config_value.admin_token else "open",
            database=database,
        )

    @app.get("/", include_in_schema=False)
    async def root() -> Response:
        return FileResponse(static_dir / "index.html")

    @app.get("/admin", include_in_schema=False)
    async def admin_console() -> Response:
        return FileResponse(static_dir / "index.html")

    @app.post("/api/projects", response_model=ProjectResponse, status_code=201)
    async def create_project(payload: ProjectCreateRequest, request: Request, response: Response) -> ProjectResponse:
        project = app.state.store.create_project(
            name=payload.name,
            description=payload.description,
            default_user_brief=payload.default_user_brief,
            default_target_chapters=payload.default_target_chapters,
        )
        audit(
            request=request,
            response=response,
            status_code=201,
            action="project.create",
            resource_type="project",
            resource_id=project.project_id,
            project_id=project.project_id,
            run_id=None,
            approval_id=None,
            payload={"name": project.name},
        )
        return ProjectResponse.model_validate(project.__dict__)

    @app.get("/api/projects", response_model=list[ProjectResponse])
    async def list_projects() -> list[ProjectResponse]:
        return [ProjectResponse.model_validate(project.__dict__) for project in app.state.store.list_projects()]

    @app.get("/api/projects/{project_id}", response_model=ProjectResponse)
    async def get_project(project_id: str) -> ProjectResponse:
        project = app.state.store.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="project_not_found")
        return ProjectResponse.model_validate(project.__dict__)

    @app.post("/api/projects/{project_id}/runs", response_model=RunResponse, status_code=201)
    async def create_run(project_id: str, payload: RunCreateRequest, request: Request, response: Response) -> RunResponse:
        project = app.state.store.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="project_not_found")

        is_continuation = False
        request_payload = app.state.workflow.prepare_project_request(
            project=project,
            user_brief=payload.user_brief,
            target_chapters=payload.target_chapters,
            operator_id=payload.operator_id,
            quick_mode=payload.quick_mode,
        )
        if payload.user_brief is None and payload.target_chapters is None and not payload.quick_mode:
            source_run = next(
                (item for item in app.state.store.list_runs(project_id) if item.status == "completed"),
                None,
            )
            if source_run and app.state.store.list_chapters(project_id):
                source_artifacts = [item.__dict__ for item in app.state.store.list_artifacts(source_run.run_id)]
                request_payload = app.state.workflow.prepare_continuation_request(
                    project=project,
                    original_request=source_run.request,
                    artifacts=source_artifacts,
                    operator_id=payload.operator_id or request.state.actor,
                )
                is_continuation = True
        request_payload = merge_conversation_decisions_into_request(
            project_id=project_id,
            request_payload=request_payload,
        )
        run = app.state.store.save_run(
            project_id=project_id,
            status="running",
            request=request_payload,
            result=initial_progress_snapshot(current_node="interviewer_contract"),
            error=None,
        )
        if is_continuation:
            def work(on_update):
                return app.state.workflow.run_followup(
                    project=project,
                    request_payload=request_payload,
                    on_update=on_update,
                )
        else:
            def work(on_update):
                return app.state.workflow.run_project(
                    project=project,
                    request_payload=request_payload,
                    on_update=on_update,
                )
        launch_background_run(
            run_id=run.run_id,
            work=work,
        )

        audit(
            request=request,
            response=response,
            status_code=201,
            action="run.create",
            resource_type="run",
            resource_id=run.run_id,
            project_id=project_id,
            run_id=run.run_id,
            approval_id=None,
            payload={
                "target_chapters": run.request["target_chapters"],
                "operator_id": run.request["operator_id"],
                "status": run.status,
                "quick_mode": run.request.get("quick_mode", False),
                "continuation": is_continuation,
            },
        )
        return RunResponse.model_validate(run.__dict__)

    @app.post("/api/runs/{run_id}/mark-failed", response_model=RunResponse)
    async def mark_run_failed(run_id: str, request: Request, response: Response) -> RunResponse:
        run = app.state.store.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="run_not_found")
        if run.status != "running":
            raise HTTPException(status_code=409, detail="run_not_running")

        reason = "人工标记失败；建议忽略该 Run 并重新尝试。"
        updated_run = app.state.store.update_run(
            run_id=run_id,
            status="failed",
            result=build_manual_failure_result(run, reason=reason, operator_id=request.state.actor),
            error=reason,
        )
        if not updated_run:
            raise HTTPException(status_code=409, detail="run_state_changed")

        audit(
            request=request,
            response=response,
            status_code=200,
            action="run.mark_failed",
            resource_type="run",
            resource_id=run_id,
            project_id=run.project_id,
            run_id=run_id,
            approval_id=None,
            payload={"reason": reason},
        )
        return RunResponse.model_validate(enrich_run_payload(updated_run))

    @app.post("/api/runs/{run_id}/retry", response_model=RunResponse, status_code=201)
    async def retry_run(run_id: str, request: Request, response: Response) -> RunResponse:
        previous_run = app.state.store.get_run(run_id)
        if not previous_run:
            raise HTTPException(status_code=404, detail="run_not_found")
        if previous_run.status == "running":
            raise HTTPException(status_code=409, detail="run_still_running")

        project = app.state.store.get_project(previous_run.project_id)
        if not project:
            raise HTTPException(status_code=404, detail="project_not_found")

        request_payload = dict(previous_run.request)
        request_payload["operator_id"] = request.state.actor
        request_payload = merge_conversation_decisions_into_request(
            project_id=project.project_id,
            request_payload=request_payload,
        )
        run = app.state.store.save_run(
            project_id=project.project_id,
            status="running",
            request=request_payload,
            result=initial_progress_snapshot(current_node="interviewer_contract"),
            error=None,
        )
        launch_background_run(
            run_id=run.run_id,
            work=lambda on_update: app.state.workflow.run_project(
                project=project,
                request_payload=request_payload,
                on_update=on_update,
            ),
        )

        audit(
            request=request,
            response=response,
            status_code=201,
            action="run.retry",
            resource_type="run",
            resource_id=run.run_id,
            project_id=project.project_id,
            run_id=run.run_id,
            approval_id=None,
            payload={"source_run_id": previous_run.run_id},
        )
        return RunResponse.model_validate(run.__dict__)

    @app.get("/api/runs/{run_id}", response_model=RunResponse)
    async def get_run(run_id: str) -> RunResponse:
        run = app.state.store.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="run_not_found")
        run = maybe_finalize_stale_run(run)
        return RunResponse.model_validate(enrich_run_payload(run))

    @app.get("/api/projects/{project_id}/runs", response_model=list[RunResponse])
    async def list_runs(project_id: str) -> list[RunResponse]:
        project = app.state.store.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="project_not_found")
        return [
            RunResponse.model_validate(enrich_run_payload(maybe_finalize_stale_run(item)))
            for item in app.state.store.list_runs(project_id)
        ]

    @app.get("/api/projects/{project_id}/chapters", response_model=list[ChapterResponse])
    async def list_chapters(project_id: str) -> list[ChapterResponse]:
        project = app.state.store.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="project_not_found")
        return [ChapterResponse.model_validate(item.__dict__) for item in app.state.store.list_chapters(project_id)]

    @app.get("/api/runs/{run_id}/artifacts", response_model=list[ArtifactResponse])
    async def list_run_artifacts(run_id: str) -> list[ArtifactResponse]:
        run = app.state.store.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="run_not_found")
        run = maybe_finalize_stale_run(run)
        stored = [ArtifactResponse.model_validate(item.__dict__) for item in app.state.store.list_artifacts(run_id)]
        if run.status != "running":
            return stored

        live_artifacts = (run.result or {}).get("live_artifacts") or []
        if not live_artifacts:
            return stored

        seen_types = {item.artifact_type for item in stored}
        synthetic: list[ArtifactResponse] = []
        created_at = ((run.result or {}).get("progress") or {}).get("updated_at") or run.created_at
        for index, item in enumerate(live_artifacts):
            artifact_type = item.get("artifact_type")
            if artifact_type in seen_types:
                continue
            synthetic.append(
                ArtifactResponse(
                    artifact_id=f"live_{run_id}_{index}",
                    run_id=run.run_id,
                    project_id=run.project_id,
                    chapter_no=((run.result or {}).get("progress") or {}).get("chapter_no"),
                    artifact_type=str(artifact_type),
                    payload=item.get("payload"),
                    created_at=created_at,
                )
            )
        return synthetic + stored

    @app.post("/api/runs/{run_id}/approval-requests", response_model=ApprovalRequestResponse, status_code=201)
    async def create_approval_request(
        run_id: str,
        payload: ApprovalRequestCreateRequest,
        request: Request,
        response: Response,
    ) -> ApprovalRequestResponse:
        run = app.state.store.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="run_not_found")
        approval = app.state.store.create_approval_request(
            project_id=run.project_id,
            run_id=run_id,
            chapter_no=payload.chapter_no,
            requested_action=payload.requested_action,
            reason=payload.reason,
            payload=payload.payload,
        )
        audit(
            request=request,
            response=response,
            status_code=201,
            action="approval_request.create",
            resource_type="approval_request",
            resource_id=approval.approval_id,
            project_id=run.project_id,
            run_id=run_id,
            approval_id=approval.approval_id,
            payload={
                "requested_action": approval.requested_action,
                "chapter_no": approval.chapter_no,
            },
        )
        return ApprovalRequestResponse.model_validate(approval.__dict__)

    @app.get("/api/approval-requests/{approval_id}", response_model=ApprovalRequestResponse)
    async def get_approval_request(approval_id: str) -> ApprovalRequestResponse:
        approval = app.state.store.get_approval_request(approval_id)
        if not approval:
            raise HTTPException(status_code=404, detail="approval_request_not_found")
        return ApprovalRequestResponse.model_validate(approval.__dict__)

    @app.get("/api/projects/{project_id}/approval-requests", response_model=list[ApprovalRequestResponse])
    async def list_project_approval_requests(project_id: str) -> list[ApprovalRequestResponse]:
        project = app.state.store.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="project_not_found")
        return [
            ApprovalRequestResponse.model_validate(item.__dict__)
            for item in app.state.store.list_approval_requests(project_id=project_id)
        ]

    @app.post("/api/approval-requests/{approval_id}/resolve", response_model=ApprovalRequestResponse)
    async def resolve_approval_request(
        approval_id: str,
        payload: ApprovalResolveRequest,
        request: Request,
        response: Response,
    ) -> ApprovalRequestResponse:
        approval = app.state.store.resolve_approval_request(
            approval_id=approval_id,
            decision=payload.decision,
            operator_id=payload.operator_id,
            comment=payload.comment,
        )
        if not approval:
            raise HTTPException(status_code=404, detail="approval_request_not_found")
        audit(
            request=request,
            response=response,
            status_code=200,
            action="approval_request.resolve",
            resource_type="approval_request",
            resource_id=approval.approval_id,
            project_id=approval.project_id,
            run_id=approval.run_id,
            approval_id=approval.approval_id,
            payload={
                "decision": payload.decision,
                "operator_id": payload.operator_id,
            },
        )
        return ApprovalRequestResponse.model_validate(approval.__dict__)

    @app.post("/api/approval-requests/{approval_id}/execute", response_model=ApprovalExecuteResponse)
    async def execute_approval_request(
        approval_id: str,
        request: Request,
        response: Response,
        payload: ApprovalExecuteRequest | None = Body(default=None),
    ) -> ApprovalExecuteResponse:
        approval = app.state.store.get_approval_request(approval_id)
        if not approval:
            raise HTTPException(status_code=404, detail="approval_request_not_found")
        if approval.status != "approved":
            raise HTTPException(status_code=400, detail="approval_request_must_be_approved")
        if approval.executed_run_id:
            existing_run = app.state.store.get_run(approval.executed_run_id)
            if not existing_run:
                raise HTTPException(status_code=409, detail="approval_request_execution_state_invalid")
            return ApprovalExecuteResponse(
                approval=ApprovalRequestResponse.model_validate(approval.__dict__),
                run=RunResponse.model_validate(existing_run.__dict__),
            )

        original_run = app.state.store.get_run(approval.run_id)
        if not original_run:
            raise HTTPException(status_code=404, detail="source_run_not_found")
        project = app.state.store.get_project(approval.project_id)
        if not project:
            raise HTTPException(status_code=404, detail="project_not_found")
        effective_requested_action = payload.requested_action_override if payload and payload.requested_action_override else approval.requested_action
        artifacts = [item.__dict__ for item in app.state.store.list_artifacts(approval.run_id)]
        request_payload = app.state.workflow.prepare_followup_request(
            project=project,
            original_request=original_run.request,
            artifacts=artifacts,
            approval=approval,
            requested_action=effective_requested_action,
        )
        request_payload = merge_conversation_decisions_into_request(
            project_id=project.project_id,
            request_payload=request_payload,
        )
        followup_run = app.state.store.save_run(
            project_id=project.project_id,
            status="running",
            request=request_payload,
            result=initial_progress_snapshot(current_node="interviewer_contract"),
            error=None,
        )
        updated_approval = app.state.store.mark_approval_request_executed(
            approval_id=approval_id,
            run_id=followup_run.run_id,
        )
        launch_background_run(
            run_id=followup_run.run_id,
            work=lambda on_update: app.state.workflow.run_followup(
                project=project,
                request_payload=request_payload,
                on_update=on_update,
            ),
        )
        audit(
            request=request,
            response=response,
            status_code=200,
            action="approval_request.execute",
            resource_type="approval_request",
            resource_id=approval_id,
            project_id=project.project_id,
            run_id=followup_run.run_id,
            approval_id=approval_id,
            payload={
                "requested_action": approval.requested_action,
                "executed_requested_action": effective_requested_action,
            },
        )
        if updated_approval is None:
            raise HTTPException(status_code=500, detail="approval_request_execution_persist_failed")
        return ApprovalExecuteResponse(
            approval=ApprovalRequestResponse.model_validate(updated_approval.__dict__),
            run=RunResponse.model_validate(followup_run.__dict__),
        )

    @app.get("/api/projects/{project_id}/conversation-threads", response_model=list[ConversationThreadResponse])
    async def list_conversation_threads(project_id: str) -> list[ConversationThreadResponse]:
        project = app.state.store.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="project_not_found")
        return [
            ConversationThreadResponse.model_validate(enrich_thread_payload(item))
            for item in app.state.store.list_conversation_threads(project_id)
        ]

    @app.post("/api/projects/{project_id}/conversation-threads", response_model=ConversationThreadResponse, status_code=201)
    async def create_conversation_thread(
        project_id: str,
        payload: ConversationThreadCreateRequest,
        request: Request,
        response: Response,
    ) -> ConversationThreadResponse:
        project = app.state.store.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="project_not_found")
        linked_run = None
        chapter_no = payload.linked_chapter_no
        if payload.linked_run_id:
            linked_run = app.state.store.get_run(payload.linked_run_id)
            if not linked_run or linked_run.project_id != project_id:
                raise HTTPException(status_code=404, detail="linked_run_not_found")
            chapter_no = chapter_no or infer_run_chapter(linked_run)
        thread = app.state.store.create_conversation_thread(
            project_id=project_id,
            scope=payload.scope,
            title=payload.title or conversation_title(scope=payload.scope, chapter_no=chapter_no),
            linked_run_id=payload.linked_run_id,
            linked_chapter_no=chapter_no,
        )
        opening_type, opening_content, opening_payload = build_thread_opening(
            scope=thread.scope,
            project=project,
            run=linked_run,
            chapter_no=thread.linked_chapter_no,
        )
        app.state.store.add_conversation_message(
            thread_id=thread.thread_id,
            role="assistant",
            message_type=opening_type,
            content=opening_content,
            structured_payload=opening_payload,
        )
        thread = app.state.store.get_conversation_thread(thread.thread_id) or thread
        audit(
            request=request,
            response=response,
            status_code=201,
            action="conversation_thread.create",
            resource_type="conversation_thread",
            resource_id=thread.thread_id,
            project_id=project_id,
            run_id=thread.linked_run_id,
            approval_id=None,
            payload={"scope": thread.scope, "linked_chapter_no": thread.linked_chapter_no},
        )
        return ConversationThreadResponse.model_validate(enrich_thread_payload(thread))

    @app.get("/api/conversation-threads/{thread_id}", response_model=ConversationThreadResponse)
    async def get_conversation_thread(thread_id: str) -> ConversationThreadResponse:
        thread = app.state.store.get_conversation_thread(thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="conversation_thread_not_found")
        return ConversationThreadResponse.model_validate(enrich_thread_payload(thread))

    @app.post("/api/conversation-threads/{thread_id}/apply-project-summary", response_model=ProjectResponse)
    async def apply_conversation_project_summary(
        thread_id: str,
        request: Request,
        response: Response,
    ) -> ProjectResponse:
        thread = app.state.store.get_conversation_thread(thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="conversation_thread_not_found")
        project = app.state.store.get_project(thread.project_id)
        if not project:
            raise HTTPException(status_code=404, detail="project_not_found")
        interview_state = build_interview_state(thread=thread, project=project)
        if interview_state is None or not (interview_state.get("stage_confirmation") or {}).get("project_summary"):
            raise HTTPException(status_code=409, detail="project_summary_not_ready")
        updated_brief = build_project_summary_brief(project=project, thread=thread, interview_state=interview_state)
        if updated_brief is None:
            raise HTTPException(status_code=409, detail="project_summary_not_ready")
        updated_project = app.state.store.update_project_brief(
            project_id=project.project_id,
            default_user_brief=updated_brief,
        )
        if updated_project is None:
            raise HTTPException(status_code=404, detail="project_not_found")
        app.state.store.add_conversation_message(
            thread_id=thread.thread_id,
            role="system",
            message_type="system_action_result",
            content="已把这版阶段确认摘要写回项目设定。接下来可以继续进入人物讨论或大纲讨论。",
            structured_payload={
                "source": "project_summary_apply",
                "project_id": project.project_id,
                "capture_stage": "clarified",
            },
        )
        audit(
            request=request,
            response=response,
            status_code=200,
            action="project_summary.apply",
            resource_type="project",
            resource_id=updated_project.project_id,
            project_id=updated_project.project_id,
            run_id=None,
            approval_id=None,
            payload={"thread_id": thread.thread_id, "scope": thread.scope, "capture_stage": "clarified"},
        )
        return ProjectResponse.model_validate(updated_project.__dict__)

    @app.post("/api/conversation-threads/{thread_id}/split-stage-summary", response_model=list[ConversationDecisionResponse], status_code=201)
    async def split_conversation_stage_summary(
        thread_id: str,
        request: Request,
        response: Response,
    ) -> list[ConversationDecisionResponse]:
        thread = app.state.store.get_conversation_thread(thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="conversation_thread_not_found")
        project = app.state.store.get_project(thread.project_id)
        if not project:
            raise HTTPException(status_code=404, detail="project_not_found")
        interview_state = build_interview_state(thread=thread, project=project)
        if interview_state is None:
            raise HTTPException(status_code=409, detail="stage_confirmation_not_ready")
        decision_plan = build_stage_decision_plan(thread=thread, interview_state=interview_state)
        if not decision_plan:
            raise HTTPException(status_code=409, detail="stage_confirmation_not_ready")
        existing_decisions = app.state.store.list_conversation_decisions(project_id=thread.project_id, thread_id=thread.thread_id)
        created_or_reused: list[object] = []
        for item in decision_plan:
            matched = next(
                (
                    decision
                    for decision in existing_decisions
                    if decision.decision_type == item["decision_type"]
                    and str(decision.payload.get("content") or "").strip() == item["content"]
                ),
                None,
            )
            if matched is not None:
                created_or_reused.append(matched)
                continue
            source_message = app.state.store.add_conversation_message(
                thread_id=thread.thread_id,
                role="system",
                message_type="system_action_result",
                content=f"已从阶段确认页采纳为{item['decision_type']}：{item['content']}",
                structured_payload={
                    "source": "stage_confirmation_split",
                    "source_label": item["source_label"],
                    "decision_type": item["decision_type"],
                    "content": item["content"],
                },
            )
            if source_message is None:
                raise HTTPException(status_code=404, detail="conversation_thread_not_found")
            decision = app.state.store.create_conversation_decision(
                project_id=thread.project_id,
                thread_id=thread.thread_id,
                message_id=source_message.message_id,
                decision_type=item["decision_type"],
                payload=build_conversation_decision_payload_from_content(
                    thread=thread,
                    message_id=source_message.message_id,
                    decision_type=item["decision_type"],
                    content=item["content"],
                    source="stage_confirmation",
                    source_label=item["source_label"],
                ),
                applied_to_run_id=thread.linked_run_id,
                applied_to_chapter_no=thread.linked_chapter_no,
            )
            existing_decisions.append(decision)
            created_or_reused.append(decision)
        audit(
            request=request,
            response=response,
            status_code=201,
            action="conversation_stage.split",
            resource_type="conversation_thread",
            resource_id=thread.thread_id,
            project_id=thread.project_id,
            run_id=thread.linked_run_id,
            approval_id=None,
            payload={"decision_count": len(created_or_reused)},
        )
        return [ConversationDecisionResponse.model_validate(item.__dict__) for item in created_or_reused]

    @app.get("/api/conversation-threads/{thread_id}/messages", response_model=list[ConversationMessageResponse])
    async def list_conversation_messages(thread_id: str) -> list[ConversationMessageResponse]:
        thread = app.state.store.get_conversation_thread(thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="conversation_thread_not_found")
        return [
            ConversationMessageResponse.model_validate(item.__dict__)
            for item in app.state.store.list_conversation_messages(thread_id)
        ]

    @app.post("/api/conversation-threads/{thread_id}/messages", response_model=list[ConversationMessageResponse], status_code=201)
    async def create_conversation_message(
        thread_id: str,
        payload: ConversationMessageCreateRequest,
        request: Request,
        response: Response,
    ) -> list[ConversationMessageResponse]:
        thread = app.state.store.get_conversation_thread(thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="conversation_thread_not_found")
        user_message = app.state.store.add_conversation_message(
            thread_id=thread_id,
            role="user",
            message_type="user_message",
            content=payload.content,
            structured_payload=build_interview_user_payload(
                thread=thread,
                content=payload.content,
                operator_id=request.state.actor,
            ),
        )
        if user_message is None:
            raise HTTPException(status_code=404, detail="conversation_thread_not_found")
        project = app.state.store.get_project(thread.project_id)
        linked_run = app.state.store.get_run(thread.linked_run_id) if thread.linked_run_id else None
        reply_type, reply_content, reply_payload = build_assistant_followup(
            thread=thread,
            project=project,
            run=linked_run,
            user_message=payload.content,
        )
        assistant_message = app.state.store.add_conversation_message(
            thread_id=thread_id,
            role="assistant",
            message_type=reply_type,
            content=reply_content,
            structured_payload=reply_payload,
        )
        audit(
            request=request,
            response=response,
            status_code=201,
            action="conversation_message.create",
            resource_type="conversation_message",
            resource_id=user_message.message_id,
            project_id=thread.project_id,
            run_id=thread.linked_run_id,
            approval_id=None,
            payload={"thread_id": thread_id, "message_type": "user_message"},
        )
        messages = [user_message]
        if assistant_message is not None:
            messages.append(assistant_message)
        return [ConversationMessageResponse.model_validate(item.__dict__) for item in messages]

    @app.get("/api/projects/{project_id}/conversation-decisions", response_model=list[ConversationDecisionResponse])
    async def list_conversation_decisions(project_id: str) -> list[ConversationDecisionResponse]:
        project = app.state.store.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="project_not_found")
        return [
            ConversationDecisionResponse.model_validate(item.__dict__)
            for item in app.state.store.list_conversation_decisions(project_id=project_id)
        ]

    @app.patch("/api/conversation-decisions/{decision_id}", response_model=ConversationDecisionResponse)
    async def update_conversation_decision(
        decision_id: str,
        payload: ConversationDecisionUpdateRequest,
        request: Request,
        response: Response,
    ) -> ConversationDecisionResponse:
        decision = app.state.store.get_conversation_decision(decision_id)
        if not decision:
            raise HTTPException(status_code=404, detail="conversation_decision_not_found")
        updated = app.state.store.update_conversation_decision(
            decision_id=decision_id,
            payload=rewrite_conversation_decision_payload(
                existing_payload=decision.payload,
                decision_type=decision.decision_type,
                content=payload.content.strip(),
            ),
        )
        if not updated:
            raise HTTPException(status_code=404, detail="conversation_decision_not_found")
        audit(
            request=request,
            response=response,
            status_code=200,
            action="conversation_decision.update",
            resource_type="conversation_decision",
            resource_id=updated.decision_id,
            project_id=updated.project_id,
            run_id=updated.applied_to_run_id,
            approval_id=None,
            payload={"decision_type": updated.decision_type},
        )
        return ConversationDecisionResponse.model_validate(updated.__dict__)

    @app.delete("/api/conversation-decisions/{decision_id}", status_code=204)
    async def delete_conversation_decision(
        decision_id: str,
        request: Request,
        response: Response,
    ) -> Response:
        decision = app.state.store.get_conversation_decision(decision_id)
        if not decision:
            raise HTTPException(status_code=404, detail="conversation_decision_not_found")
        deleted = app.state.store.delete_conversation_decision(decision_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="conversation_decision_not_found")
        audit(
            request=request,
            response=response,
            status_code=204,
            action="conversation_decision.delete",
            resource_type="conversation_decision",
            resource_id=decision.decision_id,
            project_id=decision.project_id,
            run_id=decision.applied_to_run_id,
            approval_id=None,
            payload={"decision_type": decision.decision_type},
        )
        return Response(status_code=204)

    @app.post("/api/conversation-threads/{thread_id}/decisions", response_model=ConversationDecisionResponse, status_code=201)
    async def create_conversation_decision_direct(
        thread_id: str,
        payload: ConversationDecisionDirectCreateRequest,
        request: Request,
        response: Response,
    ) -> ConversationDecisionResponse:
        thread = app.state.store.get_conversation_thread(thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="conversation_thread_not_found")
        source_label = payload.source_label or "当前理解草案"
        source_message = app.state.store.add_conversation_message(
            thread_id=thread.thread_id,
            role="system",
            message_type="system_action_result",
            content=f"已从{source_label}采纳为{payload.decision_type}：{payload.content}",
            structured_payload={
                "source": "draft_recap_adoption",
                "source_label": source_label,
                "decision_type": payload.decision_type,
                "content": payload.content,
            },
        )
        if source_message is None:
            raise HTTPException(status_code=404, detail="conversation_thread_not_found")
        decision = app.state.store.create_conversation_decision(
            project_id=thread.project_id,
            thread_id=thread.thread_id,
            message_id=source_message.message_id,
            decision_type=payload.decision_type,
            payload=build_conversation_decision_payload_from_content(
                thread=thread,
                message_id=source_message.message_id,
                decision_type=payload.decision_type,
                content=payload.content,
                source="draft_recap",
                source_label=source_label,
            ),
            applied_to_run_id=thread.linked_run_id,
            applied_to_chapter_no=thread.linked_chapter_no,
        )
        audit(
            request=request,
            response=response,
            status_code=201,
            action="conversation_decision.create",
            resource_type="conversation_decision",
            resource_id=decision.decision_id,
            project_id=thread.project_id,
            run_id=thread.linked_run_id,
            approval_id=None,
            payload={"decision_type": payload.decision_type, "thread_id": thread.thread_id, "source_label": source_label},
        )
        return ConversationDecisionResponse.model_validate(decision.__dict__)

    @app.post("/api/conversation-messages/{message_id}/adopt", response_model=ConversationDecisionResponse, status_code=201)
    async def adopt_conversation_message(
        message_id: str,
        payload: ConversationDecisionCreateRequest,
        request: Request,
        response: Response,
    ) -> ConversationDecisionResponse:
        message = app.state.store.get_conversation_message(message_id)
        if not message:
            raise HTTPException(status_code=404, detail="conversation_message_not_found")
        thread = app.state.store.get_conversation_thread(message.thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="conversation_thread_not_found")
        decision = app.state.store.create_conversation_decision(
            project_id=thread.project_id,
            thread_id=thread.thread_id,
            message_id=message_id,
            decision_type=payload.decision_type,
            payload=build_conversation_decision_payload(
                thread=thread,
                message=message,
                decision_type=payload.decision_type,
            ),
            applied_to_run_id=thread.linked_run_id,
            applied_to_chapter_no=thread.linked_chapter_no,
        )
        audit(
            request=request,
            response=response,
            status_code=201,
            action="conversation_message.adopt",
            resource_type="conversation_decision",
            resource_id=decision.decision_id,
            project_id=thread.project_id,
            run_id=thread.linked_run_id,
            approval_id=None,
            payload={"decision_type": payload.decision_type, "message_id": message_id},
        )
        return ConversationDecisionResponse.model_validate(decision.__dict__)

    @app.get("/api/audit-logs", response_model=list[AuditLogResponse])
    async def list_audit_logs(limit: int = 100) -> list[AuditLogResponse]:
        safe_limit = max(1, min(limit, 500))
        return [AuditLogResponse.model_validate(item.__dict__) for item in app.state.store.list_audit_logs(limit=safe_limit)]

    return app


app = create_app()
