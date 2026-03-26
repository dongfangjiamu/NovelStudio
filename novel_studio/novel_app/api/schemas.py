from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    stub_mode: bool
    model_name: str
    auth_mode: Literal["open", "token"]
    database: dict[str, str | None]


class ApiErrorResponse(BaseModel):
    detail: str


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    default_user_brief: dict[str, Any] = Field(default_factory=dict)
    default_target_chapters: int = Field(default=1, ge=1, le=100)


class ProjectResponse(BaseModel):
    project_id: str
    name: str
    description: str | None
    default_user_brief: dict[str, Any]
    default_target_chapters: int
    created_at: str


class RunCreateRequest(BaseModel):
    user_brief: dict[str, Any] | None = None
    target_chapters: int | None = Field(default=None, ge=1, le=100)
    operator_id: str | None = Field(default=None, min_length=1, max_length=120)
    quick_mode: bool = False


class RunRequestPayload(BaseModel):
    user_brief: dict[str, Any]
    target_chapters: int
    operator_id: str
    quick_mode: bool = False
    human_instruction: dict[str, Any] | None = None


class RunResponse(BaseModel):
    run_id: str
    project_id: str
    status: Literal["running", "completed", "failed", "awaiting_approval"]
    created_at: str
    finished_at: str | None = None
    request: RunRequestPayload
    result: dict[str, Any] | None = None
    error: str | None = None
    artifact_count: int = 0
    has_artifacts: bool = False


class ChapterResponse(BaseModel):
    chapter_id: str
    project_id: str
    chapter_no: int
    title: str
    status: str
    run_id: str
    created_at: str
    updated_at: str


class ArtifactResponse(BaseModel):
    artifact_id: str
    run_id: str
    project_id: str
    chapter_no: int | None = None
    artifact_type: str
    payload: dict[str, Any] | list[Any] | str | None
    created_at: str


class ApprovalRequestCreateRequest(BaseModel):
    requested_action: Literal["continue", "rewrite", "replan", "human_check"] = "continue"
    reason: str = Field(min_length=1, max_length=500)
    chapter_no: int | None = Field(default=None, ge=1)
    payload: dict[str, Any] = Field(default_factory=dict)


class ApprovalResolveRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    operator_id: str = Field(min_length=1, max_length=120)
    comment: str | None = Field(default=None, max_length=1000)


class ApprovalRequestResponse(BaseModel):
    approval_id: str
    project_id: str
    run_id: str
    chapter_no: int | None = None
    status: Literal["pending", "approved", "rejected"]
    requested_action: str
    reason: str
    payload: dict[str, Any]
    created_at: str
    resolved_at: str | None = None
    resolution_operator_id: str | None = None
    resolution_comment: str | None = None
    executed_run_id: str | None = None
    executed_at: str | None = None


class AuditLogResponse(BaseModel):
    audit_id: str
    project_id: str | None = None
    run_id: str | None = None
    approval_id: str | None = None
    actor: str
    action: str
    resource_type: str
    resource_id: str | None = None
    request_id: str
    path: str
    method: str
    status_code: int
    payload: dict[str, Any]
    created_at: str


class ApprovalExecuteResponse(BaseModel):
    approval: ApprovalRequestResponse
    run: RunResponse
