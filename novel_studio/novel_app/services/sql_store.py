from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select, text

from novel_app.db import (
    Base,
    create_engine_and_session_factory,
    get_database_backend,
    ping_database,
    session_scope,
)
from novel_app.db_models import (
    ApprovalRequestModel,
    ArtifactModel,
    AuditLogModel,
    ChapterModel,
    ConversationDecisionModel,
    ConversationMessageModel,
    ConversationThreadModel,
    ProjectModel,
    RunModel,
)
from novel_app.services.store import (
    ApprovalRequestRecord,
    ArtifactRecord,
    AuditLogRecord,
    ChapterRecord,
    ConversationDecisionRecord,
    ConversationMessageRecord,
    ConversationThreadRecord,
    ProjectRecord,
    RunRecord,
    utc_now_iso,
)


class SqlAlchemyStore:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self.engine, self.session_factory = create_engine_and_session_factory(database_url)

    def create_tables(self) -> None:
        Base.metadata.create_all(self.engine)
        if get_database_backend(self.database_url) == "postgresql":
            with self.engine.begin() as connection:
                connection.execute(text("ALTER TABLE runs ALTER COLUMN finished_at DROP NOT NULL"))
                connection.execute(text("UPDATE runs SET finished_at = NULL WHERE status = 'running'"))

    @staticmethod
    def _project_record(row: ProjectModel) -> ProjectRecord:
        return ProjectRecord(
            project_id=row.project_id,
            name=row.name,
            description=row.description,
            default_user_brief=row.default_user_brief,
            default_target_chapters=row.default_target_chapters,
            created_at=row.created_at,
        )

    @staticmethod
    def _run_record(row: RunModel) -> RunRecord:
        return RunRecord(
            run_id=row.run_id,
            project_id=row.project_id,
            status=row.status,
            created_at=row.created_at,
            finished_at=row.finished_at,
            request=row.request,
            result=row.result,
            error=row.error,
        )

    @staticmethod
    def _chapter_record(row: ChapterModel) -> ChapterRecord:
        return ChapterRecord(
            chapter_id=row.chapter_id,
            project_id=row.project_id,
            chapter_no=row.chapter_no,
            title=row.title,
            status=row.status,
            run_id=row.run_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _artifact_record(row: ArtifactModel) -> ArtifactRecord:
        return ArtifactRecord(
            artifact_id=row.artifact_id,
            run_id=row.run_id,
            project_id=row.project_id,
            chapter_no=row.chapter_no,
            artifact_type=row.artifact_type,
            payload=row.payload,
            created_at=row.created_at,
        )

    @staticmethod
    def _approval_record(row: ApprovalRequestModel) -> ApprovalRequestRecord:
        return ApprovalRequestRecord(
            approval_id=row.approval_id,
            project_id=row.project_id,
            run_id=row.run_id,
            chapter_no=row.chapter_no,
            status=row.status,
            requested_action=row.requested_action,
            reason=row.reason,
            payload=row.payload,
            created_at=row.created_at,
            resolved_at=row.resolved_at,
            resolution_operator_id=row.resolution_operator_id,
            resolution_comment=row.resolution_comment,
            executed_run_id=row.executed_run_id,
            executed_at=row.executed_at,
        )

    @staticmethod
    def _audit_record(row: AuditLogModel) -> AuditLogRecord:
        return AuditLogRecord(
            audit_id=row.audit_id,
            project_id=row.project_id,
            run_id=row.run_id,
            approval_id=row.approval_id,
            actor=row.actor,
            action=row.action,
            resource_type=row.resource_type,
            resource_id=row.resource_id,
            request_id=row.request_id,
            path=row.path,
            method=row.method,
            status_code=row.status_code,
            payload=row.payload,
            created_at=row.created_at,
        )

    @staticmethod
    def _conversation_thread_record(row: ConversationThreadModel) -> ConversationThreadRecord:
        return ConversationThreadRecord(
            thread_id=row.thread_id,
            project_id=row.project_id,
            scope=row.scope,
            status=row.status,
            title=row.title,
            linked_run_id=row.linked_run_id,
            linked_chapter_no=row.linked_chapter_no,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _conversation_message_record(row: ConversationMessageModel) -> ConversationMessageRecord:
        return ConversationMessageRecord(
            message_id=row.message_id,
            thread_id=row.thread_id,
            project_id=row.project_id,
            role=row.role,
            message_type=row.message_type,
            content=row.content,
            structured_payload=row.structured_payload,
            created_at=row.created_at,
        )

    @staticmethod
    def _conversation_decision_record(row: ConversationDecisionModel) -> ConversationDecisionRecord:
        return ConversationDecisionRecord(
            decision_id=row.decision_id,
            project_id=row.project_id,
            thread_id=row.thread_id,
            message_id=row.message_id,
            decision_type=row.decision_type,
            payload=row.payload,
            applied_to_run_id=row.applied_to_run_id,
            applied_to_chapter_no=row.applied_to_chapter_no,
            created_at=row.created_at,
        )

    def create_project(
        self,
        *,
        name: str,
        description: str | None,
        default_user_brief: dict,
        default_target_chapters: int,
    ) -> ProjectRecord:
        project = ProjectRecord(
            project_id=f"proj_{uuid4().hex[:12]}",
            name=name,
            description=description,
            default_user_brief=default_user_brief,
            default_target_chapters=default_target_chapters,
            created_at=utc_now_iso(),
        )
        with session_scope(self.session_factory) as session:
            session.add(ProjectModel(**project.__dict__))
        return project

    def list_projects(self) -> list[ProjectRecord]:
        with session_scope(self.session_factory) as session:
            rows = session.execute(select(ProjectModel).order_by(ProjectModel.created_at)).scalars().all()
            return [self._project_record(row) for row in rows]

    def get_project(self, project_id: str) -> ProjectRecord | None:
        with session_scope(self.session_factory) as session:
            row = session.get(ProjectModel, project_id)
            if row is None:
                return None
            return self._project_record(row)

    def update_project_brief(self, *, project_id: str, default_user_brief: dict) -> ProjectRecord | None:
        with session_scope(self.session_factory) as session:
            row = session.get(ProjectModel, project_id)
            if row is None:
                return None
            row.default_user_brief = default_user_brief
            session.add(row)
            session.flush()
            return self._project_record(row)

    def save_run(
        self,
        *,
        project_id: str,
        status: str,
        request: dict,
        result: dict | None,
        error: str | None,
    ) -> RunRecord:
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
        with session_scope(self.session_factory) as session:
            session.add(RunModel(**run.__dict__))
        return run

    def update_run(
        self,
        *,
        run_id: str,
        status: str,
        result: dict | None,
        error: str | None,
        only_if_status_in: set[str] | None = None,
    ) -> RunRecord | None:
        with session_scope(self.session_factory) as session:
            row = session.get(RunModel, run_id)
            if row is None:
                return None
            if only_if_status_in is not None and row.status not in only_if_status_in:
                return None
            row.status = status
            row.result = result
            row.error = error
            if status != "running":
                row.finished_at = utc_now_iso()
            session.add(row)
            session.flush()
            return self._run_record(row)

    def get_run(self, run_id: str) -> RunRecord | None:
        with session_scope(self.session_factory) as session:
            row = session.get(RunModel, run_id)
            if row is None:
                return None
            return self._run_record(row)

    def list_runs(self, project_id: str) -> list[RunRecord]:
        with session_scope(self.session_factory) as session:
            rows = session.execute(
                select(RunModel)
                .where(RunModel.project_id == project_id)
                .order_by(RunModel.created_at.desc())
            ).scalars().all()
            return [self._run_record(row) for row in rows]

    def save_run_outputs(self, *, run: RunRecord, result: dict) -> None:
        publish_package = result.get("publish_package") or {}
        current_card = result.get("current_card") or {}
        current_draft = result.get("current_draft") or {}
        chapter_no = publish_package.get("chapter_no") or current_card.get("chapter_no")
        title = publish_package.get("title") or current_draft.get("title") or f"第{chapter_no or 0}章"

        with session_scope(self.session_factory) as session:
            if chapter_no is not None:
                existing = session.execute(
                    select(ChapterModel).where(
                        ChapterModel.project_id == run.project_id,
                        ChapterModel.chapter_no == chapter_no,
                    )
                ).scalar_one_or_none()
                now = utc_now_iso()
                chapter = ChapterModel(
                    chapter_id=existing.chapter_id if existing else f"chap_{uuid4().hex[:12]}",
                    project_id=run.project_id,
                    chapter_no=chapter_no,
                    title=title,
                    status=run.status,
                    run_id=run.run_id,
                    created_at=existing.created_at if existing else now,
                    updated_at=now,
                )
                if existing:
                    session.delete(existing)
                    session.flush()
                session.add(chapter)

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
                "human_checkpoint",
                "blockers",
                "event_log",
            ]:
                if artifact_type in result and result.get(artifact_type) is not None:
                    session.add(
                        ArtifactModel(
                            artifact_id=f"art_{uuid4().hex[:12]}",
                            run_id=run.run_id,
                            project_id=run.project_id,
                            chapter_no=chapter_no,
                            artifact_type=artifact_type,
                            payload=result.get(artifact_type),
                            created_at=utc_now_iso(),
                        )
                    )

    def list_chapters(self, project_id: str) -> list[ChapterRecord]:
        with session_scope(self.session_factory) as session:
            rows = session.execute(
                select(ChapterModel)
                .where(ChapterModel.project_id == project_id)
                .order_by(ChapterModel.chapter_no)
            ).scalars().all()
            return [self._chapter_record(row) for row in rows]

    def list_artifacts(self, run_id: str) -> list[ArtifactRecord]:
        with session_scope(self.session_factory) as session:
            rows = session.execute(
                select(ArtifactModel)
                .where(ArtifactModel.run_id == run_id)
                .order_by(ArtifactModel.created_at)
            ).scalars().all()
            return [self._artifact_record(row) for row in rows]

    def create_approval_request(
        self,
        *,
        project_id: str,
        run_id: str,
        chapter_no: int | None,
        requested_action: str,
        reason: str,
        payload: dict,
    ) -> ApprovalRequestRecord:
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
        with session_scope(self.session_factory) as session:
            session.add(ApprovalRequestModel(**approval.__dict__))
        return approval

    def get_approval_request(self, approval_id: str) -> ApprovalRequestRecord | None:
        with session_scope(self.session_factory) as session:
            row = session.get(ApprovalRequestModel, approval_id)
            if row is None:
                return None
            return self._approval_record(row)

    def list_approval_requests(self, project_id: str | None = None) -> list[ApprovalRequestRecord]:
        with session_scope(self.session_factory) as session:
            stmt = select(ApprovalRequestModel).order_by(ApprovalRequestModel.created_at.desc())
            if project_id is not None:
                stmt = stmt.where(ApprovalRequestModel.project_id == project_id)
            rows = session.execute(stmt).scalars().all()
            return [self._approval_record(row) for row in rows]

    def resolve_approval_request(
        self,
        *,
        approval_id: str,
        decision: str,
        operator_id: str,
        comment: str | None,
    ) -> ApprovalRequestRecord | None:
        with session_scope(self.session_factory) as session:
            row = session.get(ApprovalRequestModel, approval_id)
            if row is None:
                return None
            row.status = decision
            row.resolved_at = utc_now_iso()
            row.resolution_operator_id = operator_id
            row.resolution_comment = comment
            session.add(row)
            session.flush()
            return self._approval_record(row)

    def mark_approval_request_executed(
        self,
        *,
        approval_id: str,
        run_id: str,
    ) -> ApprovalRequestRecord | None:
        with session_scope(self.session_factory) as session:
            row = session.get(ApprovalRequestModel, approval_id)
            if row is None:
                return None
            row.executed_run_id = run_id
            row.executed_at = utc_now_iso()
            session.add(row)
            session.flush()
            return self._approval_record(row)

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
        payload: dict,
    ) -> AuditLogRecord:
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
        with session_scope(self.session_factory) as session:
            session.add(AuditLogModel(**audit.__dict__))
        return audit

    def list_audit_logs(self, *, limit: int = 100) -> list[AuditLogRecord]:
        with session_scope(self.session_factory) as session:
            rows = session.execute(
                select(AuditLogModel).order_by(AuditLogModel.created_at.desc()).limit(limit)
            ).scalars().all()
            return [self._audit_record(row) for row in rows]

    def create_conversation_thread(
        self,
        *,
        project_id: str,
        scope: str,
        title: str,
        linked_run_id: str | None,
        linked_chapter_no: int | None,
    ) -> ConversationThreadRecord:
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
        with session_scope(self.session_factory) as session:
            session.add(ConversationThreadModel(**thread.__dict__))
        return thread

    def get_conversation_thread(self, thread_id: str) -> ConversationThreadRecord | None:
        with session_scope(self.session_factory) as session:
            row = session.get(ConversationThreadModel, thread_id)
            if row is None:
                return None
            return self._conversation_thread_record(row)

    def list_conversation_threads(self, project_id: str) -> list[ConversationThreadRecord]:
        with session_scope(self.session_factory) as session:
            rows = session.execute(
                select(ConversationThreadModel)
                .where(ConversationThreadModel.project_id == project_id)
                .order_by(ConversationThreadModel.updated_at.desc())
            ).scalars().all()
            return [self._conversation_thread_record(row) for row in rows]

    def add_conversation_message(
        self,
        *,
        thread_id: str,
        role: str,
        message_type: str,
        content: str,
        structured_payload: dict | None,
    ) -> ConversationMessageRecord | None:
        with session_scope(self.session_factory) as session:
            thread = session.get(ConversationThreadModel, thread_id)
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
            session.add(ConversationMessageModel(**message.__dict__))
            thread.updated_at = message.created_at
            session.add(thread)
            session.flush()
            return message

    def list_conversation_messages(self, thread_id: str) -> list[ConversationMessageRecord]:
        with session_scope(self.session_factory) as session:
            rows = session.execute(
                select(ConversationMessageModel)
                .where(ConversationMessageModel.thread_id == thread_id)
                .order_by(ConversationMessageModel.created_at)
            ).scalars().all()
            return [self._conversation_message_record(row) for row in rows]

    def get_conversation_message(self, message_id: str) -> ConversationMessageRecord | None:
        with session_scope(self.session_factory) as session:
            row = session.get(ConversationMessageModel, message_id)
            if row is None:
                return None
            return self._conversation_message_record(row)

    def create_conversation_decision(
        self,
        *,
        project_id: str,
        thread_id: str,
        message_id: str,
        decision_type: str,
        payload: dict,
        applied_to_run_id: str | None,
        applied_to_chapter_no: int | None,
    ) -> ConversationDecisionRecord:
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
        with session_scope(self.session_factory) as session:
            session.add(ConversationDecisionModel(**decision.__dict__))
        return decision

    def list_conversation_decisions(
        self,
        *,
        project_id: str | None = None,
        thread_id: str | None = None,
    ) -> list[ConversationDecisionRecord]:
        with session_scope(self.session_factory) as session:
            stmt = select(ConversationDecisionModel).order_by(ConversationDecisionModel.created_at.desc())
            if project_id is not None:
                stmt = stmt.where(ConversationDecisionModel.project_id == project_id)
            if thread_id is not None:
                stmt = stmt.where(ConversationDecisionModel.thread_id == thread_id)
            rows = session.execute(stmt).scalars().all()
            return [self._conversation_decision_record(row) for row in rows]

    def get_conversation_decision(self, decision_id: str) -> ConversationDecisionRecord | None:
        with session_scope(self.session_factory) as session:
            row = session.get(ConversationDecisionModel, decision_id)
            if row is None:
                return None
            return self._conversation_decision_record(row)

    def update_conversation_decision(
        self,
        *,
        decision_id: str,
        payload: dict,
    ) -> ConversationDecisionRecord | None:
        with session_scope(self.session_factory) as session:
            row = session.get(ConversationDecisionModel, decision_id)
            if row is None:
                return None
            row.payload = payload
            session.add(row)
            session.flush()
            return self._conversation_decision_record(row)

    def delete_conversation_decision(self, decision_id: str) -> bool:
        with session_scope(self.session_factory) as session:
            row = session.get(ConversationDecisionModel, decision_id)
            if row is None:
                return False
            session.delete(row)
            return True

    def health_status(self) -> dict[str, str | None]:
        ready, detail = ping_database(self.engine)
        return {
            "status": "ready" if ready else "error",
            "backend": get_database_backend(self.database_url),
            "detail": detail,
        }
