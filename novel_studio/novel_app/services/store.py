from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import RLock
from typing import Any
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ProjectRecord:
    project_id: str
    name: str
    description: str | None
    default_user_brief: dict[str, Any]
    default_target_chapters: int
    created_at: str


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    project_id: str
    status: str
    created_at: str
    finished_at: str | None
    request: dict[str, Any]
    result: dict[str, Any] | None
    error: str | None


@dataclass(frozen=True)
class ChapterRecord:
    chapter_id: str
    project_id: str
    chapter_no: int
    title: str
    status: str
    run_id: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class ArtifactRecord:
    artifact_id: str
    run_id: str
    project_id: str
    chapter_no: int | None
    artifact_type: str
    payload: Any
    created_at: str


@dataclass(frozen=True)
class ApprovalRequestRecord:
    approval_id: str
    project_id: str
    run_id: str
    chapter_no: int | None
    status: str
    requested_action: str
    reason: str
    payload: dict[str, Any]
    created_at: str
    resolved_at: str | None
    resolution_operator_id: str | None
    resolution_comment: str | None
    executed_run_id: str | None
    executed_at: str | None


@dataclass(frozen=True)
class AuditLogRecord:
    audit_id: str
    project_id: str | None
    run_id: str | None
    approval_id: str | None
    actor: str
    action: str
    resource_type: str
    resource_id: str | None
    request_id: str
    path: str
    method: str
    status_code: int
    payload: dict[str, Any]
    created_at: str


@dataclass(frozen=True)
class ConversationThreadRecord:
    thread_id: str
    project_id: str
    scope: str
    status: str
    title: str
    linked_run_id: str | None
    linked_chapter_no: int | None
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class ConversationMessageRecord:
    message_id: str
    thread_id: str
    project_id: str
    role: str
    message_type: str
    content: str
    structured_payload: dict[str, Any] | None
    created_at: str


@dataclass(frozen=True)
class ConversationDecisionRecord:
    decision_id: str
    project_id: str
    thread_id: str
    message_id: str
    decision_type: str
    payload: dict[str, Any]
    applied_to_run_id: str | None
    applied_to_chapter_no: int | None
    created_at: str


class InMemoryStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._projects: dict[str, ProjectRecord] = {}
        self._runs: dict[str, RunRecord] = {}
        self._chapters: dict[str, ChapterRecord] = {}
        self._artifacts: dict[str, ArtifactRecord] = {}
        self._approval_requests: dict[str, ApprovalRequestRecord] = {}
        self._audit_logs: dict[str, AuditLogRecord] = {}
        self._conversation_threads: dict[str, ConversationThreadRecord] = {}
        self._conversation_messages: dict[str, ConversationMessageRecord] = {}
        self._conversation_decisions: dict[str, ConversationDecisionRecord] = {}

    def create_project(
        self,
        *,
        name: str,
        description: str | None,
        default_user_brief: dict[str, Any],
        default_target_chapters: int,
    ) -> ProjectRecord:
        with self._lock:
            project = ProjectRecord(
                project_id=f"proj_{uuid4().hex[:12]}",
                name=name,
                description=description,
                default_user_brief=default_user_brief,
                default_target_chapters=default_target_chapters,
                created_at=utc_now_iso(),
            )
            self._projects[project.project_id] = project
            return project

    def list_projects(self) -> list[ProjectRecord]:
        with self._lock:
            return sorted(self._projects.values(), key=lambda item: item.created_at)

    def get_project(self, project_id: str) -> ProjectRecord | None:
        with self._lock:
            return self._projects.get(project_id)

    def save_run(
        self,
        *,
        project_id: str,
        status: str,
        request: dict[str, Any],
        result: dict[str, Any] | None,
        error: str | None,
    ) -> RunRecord:
        with self._lock:
            timestamp = utc_now_iso()
            run = RunRecord(
                run_id=f"run_{uuid4().hex[:12]}",
                project_id=project_id,
                status=status,
                created_at=timestamp,
                finished_at=None if status == "running" else timestamp,
                request=request,
                result=result,
                error=error,
            )
            self._runs[run.run_id] = run
            return run

    def update_run(
        self,
        *,
        run_id: str,
        status: str,
        result: dict[str, Any] | None,
        error: str | None,
        only_if_status_in: set[str] | None = None,
    ) -> RunRecord | None:
        with self._lock:
            current = self._runs.get(run_id)
            if current is None:
                return None
            if only_if_status_in is not None and current.status not in only_if_status_in:
                return None
            updated = RunRecord(
                run_id=current.run_id,
                project_id=current.project_id,
                status=status,
                created_at=current.created_at,
                finished_at=utc_now_iso() if status != "running" else current.finished_at,
                request=current.request,
                result=result,
                error=error,
            )
            self._runs[run_id] = updated
            return updated

    def get_run(self, run_id: str) -> RunRecord | None:
        with self._lock:
            return self._runs.get(run_id)

    def list_runs(self, project_id: str) -> list[RunRecord]:
        with self._lock:
            return sorted(
                [item for item in self._runs.values() if item.project_id == project_id],
                key=lambda item: item.created_at,
                reverse=True,
            )

    def save_run_outputs(self, *, run: RunRecord, result: dict[str, Any]) -> None:
        with self._lock:
            chapter_no = None
            title = "未命名章节"
            publish_package = result.get("publish_package") or {}
            current_card = result.get("current_card") or {}
            current_draft = result.get("current_draft") or {}
            if publish_package:
                chapter_no = publish_package.get("chapter_no")
                title = publish_package.get("title", title)
            elif current_card:
                chapter_no = current_card.get("chapter_no")
            elif current_draft:
                title = current_draft.get("title", title)

            if chapter_no is not None:
                now = utc_now_iso()
                existing = next(
                    (
                        item
                        for item in self._chapters.values()
                        if item.project_id == run.project_id and item.chapter_no == chapter_no
                    ),
                    None,
                )
                created_at = existing.created_at if existing else now
                chapter = ChapterRecord(
                    chapter_id=existing.chapter_id if existing else f"chap_{uuid4().hex[:12]}",
                    project_id=run.project_id,
                    chapter_no=chapter_no,
                    title=title,
                    status=run.status,
                    run_id=run.run_id,
                    created_at=created_at,
                    updated_at=now,
                )
                self._chapters[chapter.chapter_id] = chapter

            for artifact_type in [
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
            ]:
                if artifact_type in result and result.get(artifact_type) is not None:
                    artifact = ArtifactRecord(
                        artifact_id=f"art_{uuid4().hex[:12]}",
                        run_id=run.run_id,
                        project_id=run.project_id,
                        chapter_no=chapter_no,
                        artifact_type=artifact_type,
                        payload=result.get(artifact_type),
                        created_at=utc_now_iso(),
                    )
                    self._artifacts[artifact.artifact_id] = artifact

    def list_chapters(self, project_id: str) -> list[ChapterRecord]:
        with self._lock:
            return sorted(
                [item for item in self._chapters.values() if item.project_id == project_id],
                key=lambda item: item.chapter_no,
            )

    def list_artifacts(self, run_id: str) -> list[ArtifactRecord]:
        with self._lock:
            return sorted(
                [item for item in self._artifacts.values() if item.run_id == run_id],
                key=lambda item: item.created_at,
            )

    def create_approval_request(
        self,
        *,
        project_id: str,
        run_id: str,
        chapter_no: int | None,
        requested_action: str,
        reason: str,
        payload: dict[str, Any],
    ) -> ApprovalRequestRecord:
        with self._lock:
            approval = ApprovalRequestRecord(
                approval_id=f"apr_{uuid4().hex[:12]}",
                project_id=project_id,
                run_id=run_id,
                chapter_no=chapter_no,
                status="pending",
                requested_action=requested_action,
                reason=reason,
                payload=payload,
                created_at=utc_now_iso(),
                resolved_at=None,
                resolution_operator_id=None,
                resolution_comment=None,
                executed_run_id=None,
                executed_at=None,
            )
            self._approval_requests[approval.approval_id] = approval
            return approval

    def get_approval_request(self, approval_id: str) -> ApprovalRequestRecord | None:
        with self._lock:
            return self._approval_requests.get(approval_id)

    def list_approval_requests(self, project_id: str | None = None) -> list[ApprovalRequestRecord]:
        with self._lock:
            items = list(self._approval_requests.values())
            if project_id is not None:
                items = [item for item in items if item.project_id == project_id]
            return sorted(items, key=lambda item: item.created_at, reverse=True)

    def resolve_approval_request(
        self,
        *,
        approval_id: str,
        decision: str,
        operator_id: str,
        comment: str | None,
    ) -> ApprovalRequestRecord | None:
        with self._lock:
            current = self._approval_requests.get(approval_id)
            if current is None:
                return None
            updated = ApprovalRequestRecord(
                approval_id=current.approval_id,
                project_id=current.project_id,
                run_id=current.run_id,
                chapter_no=current.chapter_no,
                status=decision,
                requested_action=current.requested_action,
                reason=current.reason,
                payload=current.payload,
                created_at=current.created_at,
                resolved_at=utc_now_iso(),
                resolution_operator_id=operator_id,
                resolution_comment=comment,
                executed_run_id=current.executed_run_id,
                executed_at=current.executed_at,
            )
            self._approval_requests[approval_id] = updated
            return updated

    def mark_approval_request_executed(
        self,
        *,
        approval_id: str,
        run_id: str,
    ) -> ApprovalRequestRecord | None:
        with self._lock:
            current = self._approval_requests.get(approval_id)
            if current is None:
                return None
            updated = ApprovalRequestRecord(
                approval_id=current.approval_id,
                project_id=current.project_id,
                run_id=current.run_id,
                chapter_no=current.chapter_no,
                status=current.status,
                requested_action=current.requested_action,
                reason=current.reason,
                payload=current.payload,
                created_at=current.created_at,
                resolved_at=current.resolved_at,
                resolution_operator_id=current.resolution_operator_id,
                resolution_comment=current.resolution_comment,
                executed_run_id=run_id,
                executed_at=utc_now_iso(),
            )
            self._approval_requests[approval_id] = updated
            return updated

    def create_audit_log(
        self,
        *,
        project_id: str | None,
        run_id: str | None,
        approval_id: str | None,
        actor: str,
        action: str,
        resource_type: str,
        resource_id: str | None,
        request_id: str,
        path: str,
        method: str,
        status_code: int,
        payload: dict[str, Any],
    ) -> AuditLogRecord:
        with self._lock:
            audit = AuditLogRecord(
                audit_id=f"adt_{uuid4().hex[:12]}",
                project_id=project_id,
                run_id=run_id,
                approval_id=approval_id,
                actor=actor,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                request_id=request_id,
                path=path,
                method=method,
                status_code=status_code,
                payload=payload,
                created_at=utc_now_iso(),
            )
            self._audit_logs[audit.audit_id] = audit
            return audit

    def list_audit_logs(self, *, limit: int = 100) -> list[AuditLogRecord]:
        with self._lock:
            items = sorted(self._audit_logs.values(), key=lambda item: item.created_at, reverse=True)
            return items[:limit]

    def create_conversation_thread(
        self,
        *,
        project_id: str,
        scope: str,
        title: str,
        linked_run_id: str | None,
        linked_chapter_no: int | None,
    ) -> ConversationThreadRecord:
        with self._lock:
            timestamp = utc_now_iso()
            thread = ConversationThreadRecord(
                thread_id=f"thr_{uuid4().hex[:12]}",
                project_id=project_id,
                scope=scope,
                status="open",
                title=title,
                linked_run_id=linked_run_id,
                linked_chapter_no=linked_chapter_no,
                created_at=timestamp,
                updated_at=timestamp,
            )
            self._conversation_threads[thread.thread_id] = thread
            return thread

    def get_conversation_thread(self, thread_id: str) -> ConversationThreadRecord | None:
        with self._lock:
            return self._conversation_threads.get(thread_id)

    def list_conversation_threads(self, project_id: str) -> list[ConversationThreadRecord]:
        with self._lock:
            return sorted(
                [item for item in self._conversation_threads.values() if item.project_id == project_id],
                key=lambda item: item.updated_at,
                reverse=True,
            )

    def add_conversation_message(
        self,
        *,
        thread_id: str,
        role: str,
        message_type: str,
        content: str,
        structured_payload: dict[str, Any] | None,
    ) -> ConversationMessageRecord | None:
        with self._lock:
            thread = self._conversation_threads.get(thread_id)
            if thread is None:
                return None
            message = ConversationMessageRecord(
                message_id=f"msg_{uuid4().hex[:12]}",
                thread_id=thread_id,
                project_id=thread.project_id,
                role=role,
                message_type=message_type,
                content=content,
                structured_payload=structured_payload,
                created_at=utc_now_iso(),
            )
            self._conversation_messages[message.message_id] = message
            self._conversation_threads[thread_id] = ConversationThreadRecord(
                thread_id=thread.thread_id,
                project_id=thread.project_id,
                scope=thread.scope,
                status=thread.status,
                title=thread.title,
                linked_run_id=thread.linked_run_id,
                linked_chapter_no=thread.linked_chapter_no,
                created_at=thread.created_at,
                updated_at=message.created_at,
            )
            return message

    def list_conversation_messages(self, thread_id: str) -> list[ConversationMessageRecord]:
        with self._lock:
            return sorted(
                [item for item in self._conversation_messages.values() if item.thread_id == thread_id],
                key=lambda item: item.created_at,
            )

    def get_conversation_message(self, message_id: str) -> ConversationMessageRecord | None:
        with self._lock:
            return self._conversation_messages.get(message_id)

    def create_conversation_decision(
        self,
        *,
        project_id: str,
        thread_id: str,
        message_id: str,
        decision_type: str,
        payload: dict[str, Any],
        applied_to_run_id: str | None,
        applied_to_chapter_no: int | None,
    ) -> ConversationDecisionRecord:
        with self._lock:
            decision = ConversationDecisionRecord(
                decision_id=f"dec_{uuid4().hex[:12]}",
                project_id=project_id,
                thread_id=thread_id,
                message_id=message_id,
                decision_type=decision_type,
                payload=payload,
                applied_to_run_id=applied_to_run_id,
                applied_to_chapter_no=applied_to_chapter_no,
                created_at=utc_now_iso(),
            )
            self._conversation_decisions[decision.decision_id] = decision
            return decision

    def list_conversation_decisions(
        self,
        *,
        project_id: str | None = None,
        thread_id: str | None = None,
    ) -> list[ConversationDecisionRecord]:
        with self._lock:
            items = list(self._conversation_decisions.values())
            if project_id is not None:
                items = [item for item in items if item.project_id == project_id]
            if thread_id is not None:
                items = [item for item in items if item.thread_id == thread_id]
            return sorted(items, key=lambda item: item.created_at, reverse=True)

    def health_status(self) -> dict[str, str | None]:
        return {"status": "ready", "backend": "inmemory", "detail": None}
