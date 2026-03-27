from __future__ import annotations
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from pathlib import Path
from threading import Thread

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from novel_app.api.schemas import (
    ApiErrorResponse,
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
        if run_status == "awaiting_approval":
            blockers = result.get("blockers") or []
            phase_reason = ((result.get("phase_decision") or {}).get("reason")) or "需要人工确认后继续执行"
            app.state.store.create_approval_request(
                project_id=updated_run.project_id,
                run_id=updated_run.run_id,
                chapter_no=((result.get("publish_package") or {}).get("chapter_no")),
                requested_action="continue",
                reason="；".join(blockers) if blockers else str(phase_reason),
                payload={"source": "auto"},
            )

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
                "goal": "把项目方向问清楚，形成可执行的立项基础。",
                "decision_types": ["writer_playbook_rule", "character_note", "outline_constraint"],
                "topics": [
                    {
                        "title": "一句话卖点",
                        "prompt": "请先只用一句话回答：这本书最想卖给读者的核心爽点是什么？",
                    },
                    {
                        "title": "主角核心欲望",
                        "prompt": "主角最想得到什么？如果拿不到，他会失去什么？",
                    },
                    {
                        "title": "第一卷卖点",
                        "prompt": "第一卷最想让读者追下去的东西是什么：阴谋、升级、关系、复仇，还是别的？",
                    },
                    {
                        "title": "写作禁区",
                        "prompt": "这本书最不能写歪的地方是什么？有没有你明确不接受的套路、人物走向或文风？",
                    },
                ],
                "closing_prompt": "这四项已经基本问清。下一步建议把已形成的稳定结论采纳为人物设定、卷纲约束或长期规则。",
            }
        if scope == "character_room":
            return {
                "goal": "把主角驱动、人物关系和行为边界收紧成人物设定。",
                "decision_types": ["character_note"],
                "topics": [
                    {
                        "title": "主角缺陷",
                        "prompt": "主角最关键的缺陷是什么？这个缺陷会在故事前期造成什么代价？",
                    },
                    {
                        "title": "主角真正想要什么",
                        "prompt": "主角表面上想要什么，内里真正想要什么？这两者是否冲突？",
                    },
                    {
                        "title": "关键关系张力",
                        "prompt": "谁是最关键的配角或对手？他和主角之间最大的关系张力是什么？",
                    },
                    {
                        "title": "角色边界",
                        "prompt": "主角有哪些事绝不会做？哪些行为一旦出现，就会让你觉得人物写崩了？",
                    },
                ],
                "closing_prompt": "人物核心边界已经基本清楚。下一步建议把关键结论采纳为人物设定，进入后续写作。",
            }
        if scope == "outline_room":
            return {
                "goal": "把第一卷主线和推进结构收紧成可执行的大纲约束。",
                "decision_types": ["outline_constraint"],
                "topics": [
                    {
                        "title": "第一卷主线冲突",
                        "prompt": "第一卷最核心的主线冲突是什么？它为什么足以支撑读者持续追更？",
                    },
                    {
                        "title": "升级路径",
                        "prompt": "主角在第一卷里会怎样一步步升级或逼近目标？中间至少经过哪几次关键推进？",
                    },
                    {
                        "title": "阶段反转",
                        "prompt": "第一卷中段最重要的一次反转是什么？它会怎样改变局势或认知？",
                    },
                    {
                        "title": "卷末高潮",
                        "prompt": "卷末必须兑现的高潮是什么？读者看到卷末时最应该得到哪种情绪回报？",
                    },
                ],
                "closing_prompt": "第一卷方向已经足够清楚。下一步建议把这些结论采纳为卷纲约束，再驱动章卡和正文。",
            }
        return None

    def build_interview_state(*, thread, project) -> dict | None:
        blueprint = interview_blueprint(thread.scope)
        if blueprint is None:
            return None
        messages = app.state.store.list_conversation_messages(thread.thread_id)
        user_messages = [item for item in messages if item.role == "user"]
        topics = blueprint["topics"]
        completed_count = min(len(user_messages), len(topics))
        confirmed_topics = [item["title"] for item in topics[:completed_count]]
        unresolved_topics = [item["title"] for item in topics[completed_count:]]
        next_prompt = (
            topics[completed_count]["prompt"]
            if completed_count < len(topics)
            else blueprint["closing_prompt"]
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
        if brief.get("hook"):
            basis.append(f"当前钩子：{brief['hook']}")
        return {
            "goal": blueprint["goal"],
            "completion_count": completed_count,
            "total_topics": len(topics),
            "completion_label": f"{completed_count}/{len(topics)}",
            "confirmed_topics": confirmed_topics,
            "unresolved_topics": unresolved_topics,
            "next_prompt": next_prompt,
            "basis": basis,
            "adopted_count": len(adopted),
            "adopted_highlights": [item.summary for item in adopted[:3]],
        }

    def build_thread_opening(*, scope: str, project, run, chapter_no: int | None) -> tuple[str, str, dict]:
        if scope == "project_bootstrap":
            thread_stub = SimpleNamespace(thread_id="", project_id=project.project_id, scope=scope)
            interview_state = build_interview_state(thread=thread_stub, project=project)
            brief = project.default_user_brief or {}
            title = brief.get("title") or project.name
            genre = brief.get("genre") or "未定题材"
            content = (
                f"我们先把《{title}》的立项方向问清楚。当前已知题材是 {genre}。\n\n"
                f"本线程目标：{interview_state['goal']}\n"
                f"当前进度：{interview_state['completion_label']}\n\n"
                f"先回答第 1 问：{interview_state['next_prompt']}"
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
                f"先回答第 1 问：{interview_state['next_prompt']}"
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
                f"先回答第 1 问：{interview_state['next_prompt']}"
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
                "请直接告诉我：哪些内容必须保留、这次优先修什么、哪些改法不能接受。"
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
            content = (
                f"已记录你的方向：{excerpt}\n\n"
                f"当前采访进度：{interview_state['completion_label']}。\n"
                f"已确认：{'、'.join(interview_state['confirmed_topics']) if interview_state['confirmed_topics'] else '暂未形成稳定结论'}。\n"
                f"下一问：{interview_state['next_prompt']}\n"
                f"仍待明确：{'、'.join(interview_state['unresolved_topics']) if interview_state['unresolved_topics'] else '已基本问清，可开始采纳结论。'}"
            )
            payload = {"interview_state": interview_state}
            return "assistant_question", content, payload
        if thread.scope == "character_room":
            interview_state = build_interview_state(thread=thread, project=project)
            content = (
                f"已记录人物方向：{excerpt}\n\n"
                f"当前采访进度：{interview_state['completion_label']}。\n"
                f"已确认：{'、'.join(interview_state['confirmed_topics']) if interview_state['confirmed_topics'] else '暂未形成稳定结论'}。\n"
                f"下一问：{interview_state['next_prompt']}\n"
                f"仍待明确：{'、'.join(interview_state['unresolved_topics']) if interview_state['unresolved_topics'] else '已可以采纳为人物设定。'}"
            )
            payload = {"interview_state": interview_state}
            return "assistant_question", content, payload
        if thread.scope == "outline_room":
            interview_state = build_interview_state(thread=thread, project=project)
            content = (
                f"已记录大纲方向：{excerpt}\n\n"
                f"当前采访进度：{interview_state['completion_label']}。\n"
                f"已确认：{'、'.join(interview_state['confirmed_topics']) if interview_state['confirmed_topics'] else '暂未形成稳定结论'}。\n"
                f"下一问：{interview_state['next_prompt']}\n"
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
        artifacts = [item.__dict__ for item in app.state.store.list_artifacts(approval.run_id)]
        request_payload = app.state.workflow.prepare_followup_request(
            project=project,
            original_request=original_run.request,
            artifacts=artifacts,
            approval=approval,
            requested_action=approval.requested_action,
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
            payload={"requested_action": approval.requested_action},
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
            structured_payload={"operator_id": request.state.actor},
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
