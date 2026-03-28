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


class BusinessMetricCardResponse(BaseModel):
    label: str
    value: str
    note: str
    tone: Literal["neutral", "good", "warn"] = "neutral"


class BusinessMetricSectionItemResponse(BaseModel):
    label: str
    value: str
    note: str = ""
    tone: Literal["neutral", "good", "warn"] = "neutral"


class BusinessMetricSectionResponse(BaseModel):
    title: str
    summary: str
    items: list[BusinessMetricSectionItemResponse]


class BusinessMetricsResponse(BaseModel):
    scope: Literal["system", "project"]
    project_id: str | None = None
    generated_at: str
    headline: str
    summary: str
    cards: list[BusinessMetricCardResponse]
    sections: list[BusinessMetricSectionResponse] = Field(default_factory=list)


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
    chapter_focus: str | None = Field(default=None, max_length=200)
    launch_note: str | None = Field(default=None, max_length=1000)


class RunRequestPayload(BaseModel):
    user_brief: dict[str, Any]
    target_chapters: int
    operator_id: str
    quick_mode: bool = False
    human_instruction: dict[str, Any] | None = None
    conversation_guidance: dict[str, Any] | None = None


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


class ApprovalExecuteRequest(BaseModel):
    requested_action_override: Literal["continue", "rewrite", "replan"] | None = None


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


class ConversationThreadCreateRequest(BaseModel):
    scope: Literal[
        "project_bootstrap",
        "character_room",
        "outline_room",
        "chapter_planning",
        "rewrite_intervention",
        "chapter_retro",
    ] = "project_bootstrap"
    title: str | None = Field(default=None, max_length=255)
    linked_run_id: str | None = Field(default=None, min_length=1, max_length=32)
    linked_chapter_no: int | None = Field(default=None, ge=1)


class ConversationThreadResponse(BaseModel):
    thread_id: str
    project_id: str
    scope: Literal[
        "project_bootstrap",
        "character_room",
        "outline_room",
        "chapter_planning",
        "rewrite_intervention",
        "chapter_retro",
    ]
    status: Literal["open", "resolved", "archived"]
    title: str
    linked_run_id: str | None = None
    linked_chapter_no: int | None = None
    created_at: str
    updated_at: str
    latest_message_preview: str | None = None
    message_count: int = 0
    interview_state: dict[str, Any] | None = None
    thread_context: dict[str, Any] | None = None


class ConversationMessageCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class ConversationMessageResponse(BaseModel):
    message_id: str
    thread_id: str
    project_id: str
    role: Literal["user", "assistant", "system"]
    message_type: Literal[
        "user_message",
        "assistant_question",
        "assistant_proposal",
        "assistant_diagnosis",
        "system_summary",
        "system_action_result",
    ]
    content: str
    structured_payload: dict[str, Any] | None = None
    created_at: str


class ConversationDecisionCreateRequest(BaseModel):
    decision_type: Literal[
        "human_instruction",
        "writer_playbook_rule",
        "character_note",
        "outline_constraint",
        "chapter_card_patch",
    ]


class ConversationDecisionDirectCreateRequest(BaseModel):
    decision_type: Literal[
        "human_instruction",
        "writer_playbook_rule",
        "character_note",
        "outline_constraint",
        "chapter_card_patch",
    ]
    content: str = Field(min_length=1, max_length=4000)
    source_label: str | None = Field(default=None, max_length=120)


class ConversationDecisionUpdateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class ConversationDecisionResponse(BaseModel):
    decision_id: str
    project_id: str
    thread_id: str
    message_id: str
    decision_type: Literal[
        "human_instruction",
        "writer_playbook_rule",
        "character_note",
        "outline_constraint",
        "chapter_card_patch",
    ]
    payload: dict[str, Any]
    summary: str = ""
    content: str = ""
    source: str | None = None
    source_label: str | None = None
    applied_to_run_id: str | None = None
    applied_to_chapter_no: int | None = None
    created_at: str
