from __future__ import annotations
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


def run_requires_human_approval(result: dict[str, object]) -> bool:
    phase_decision = result.get("phase_decision") or {}
    blockers = result.get("blockers") or []
    return bool(blockers) or phase_decision.get("final_decision") == "human_check"


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
            }
        }

    def build_progress_snapshot(*, state: dict[str, object], current_node: str | None) -> dict[str, object]:
        event_log = state.get("event_log") or []
        current_card = state.get("current_card") or {}
        publish_package = state.get("publish_package") or {}
        phase_decision = state.get("phase_decision") or {}
        chapter_no = publish_package.get("chapter_no") or current_card.get("chapter_no")
        return {
            "progress": {
                "current_node": current_node,
                "latest_event": event_log[-1] if event_log else None,
                "event_log_tail": event_log[-5:],
                "chapter_no": chapter_no,
                "rewrite_count": state.get("rewrite_count", 0),
                "phase_decision": phase_decision.get("final_decision"),
                "updated_at": utc_now_iso(),
            }
        }

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
        )

    def launch_background_run(*, run_id: str, work) -> None:
        def on_update(current_node: str | None, state: dict[str, object]) -> None:
            app.state.store.update_run(
                run_id=run_id,
                status="running",
                result=build_progress_snapshot(state=state, current_node=current_node),
                error=None,
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

        request_payload = app.state.workflow.prepare_project_request(
            project=project,
            user_brief=payload.user_brief,
            target_chapters=payload.target_chapters,
            operator_id=payload.operator_id,
        )
        run = app.state.store.save_run(
            project_id=project_id,
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
            },
        )
        return RunResponse.model_validate(run.__dict__)

    @app.get("/api/runs/{run_id}", response_model=RunResponse)
    async def get_run(run_id: str) -> RunResponse:
        run = app.state.store.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="run_not_found")
        return RunResponse.model_validate(run.__dict__)

    @app.get("/api/projects/{project_id}/runs", response_model=list[RunResponse])
    async def list_runs(project_id: str) -> list[RunResponse]:
        project = app.state.store.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="project_not_found")
        return [RunResponse.model_validate(item.__dict__) for item in app.state.store.list_runs(project_id)]

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
        return [ArtifactResponse.model_validate(item.__dict__) for item in app.state.store.list_artifacts(run_id)]

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

    @app.get("/api/audit-logs", response_model=list[AuditLogResponse])
    async def list_audit_logs(limit: int = 100) -> list[AuditLogResponse]:
        safe_limit = max(1, min(limit, 500))
        return [AuditLogResponse.model_validate(item.__dict__) for item in app.state.store.list_audit_logs(limit=safe_limit)]

    return app


app = create_app()
