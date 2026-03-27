from __future__ import annotations

from typing import Any

from novel_app.config import AppConfig
from novel_app.graph_main import graph
from novel_app.services.store import ApprovalRequestRecord, ProjectRecord
from novel_app.state import RuntimeContext


class WorkflowService:
    def __init__(self, config: AppConfig) -> None:
        self._config = config

    def prepare_project_request(
        self,
        *,
        project: ProjectRecord,
        user_brief: dict[str, Any] | None,
        target_chapters: int | None,
        operator_id: str | None,
        quick_mode: bool = False,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        effective_brief = user_brief or project.default_user_brief
        if not effective_brief:
            raise ValueError("user_brief is required when the project has no default_user_brief")

        effective_target_chapters = target_chapters or project.default_target_chapters
        effective_operator_id = operator_id or self._config.operator_id
        request_payload = {
            "user_brief": effective_brief,
            "target_chapters": effective_target_chapters,
            "operator_id": effective_operator_id,
        }
        if quick_mode:
            request_payload["quick_mode"] = True
            request_payload["human_instruction"] = {
                "requested_action": "quick_trial",
                "reason": "用户选择快速试写模式",
                "operator_id": effective_operator_id,
                "comment": "请优先给出更快可读的首章试写版本，控制篇幅和复杂度，先验证方向。",
                "payload": {"mode": "quick_trial"},
            }
        return request_payload

    def run_project(
        self,
        *,
        project: ProjectRecord,
        request_payload: dict[str, Any],
        on_update=None,
    ) -> dict[str, Any]:
        return self._run_graph(
            input_state={
                "user_brief": request_payload["user_brief"],
                "creative_contract": request_payload.get("creative_contract"),
                "story_bible": request_payload.get("story_bible"),
                "arc_plan": request_payload.get("arc_plan"),
                "canon_state": request_payload.get("canon_state"),
                "writer_playbook": request_payload.get("writer_playbook"),
                "chapter_lesson": request_payload.get("chapter_lesson"),
                "issue_ledger": request_payload.get("issue_ledger"),
                "target_chapters": request_payload["target_chapters"],
                "human_instruction": request_payload.get("human_instruction"),
            },
            context=RuntimeContext(
                project_id=project.project_id,
                operator_id=request_payload["operator_id"],
                model_name=self._config.model_name,
                model_provider="openai",
                openai_base_url=self._config.openai_base_url,
            ),
            on_update=on_update,
        )

    def prepare_followup_request(
        self,
        *,
        project: ProjectRecord,
        original_request: dict[str, Any],
        artifacts: list[dict[str, Any]],
        approval: ApprovalRequestRecord,
        requested_action: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        human_instruction = {
            "requested_action": requested_action,
            "reason": approval.reason,
            "operator_id": approval.resolution_operator_id,
            "comment": approval.resolution_comment,
            "payload": {
                **dict(approval.payload or {}),
                "original_requested_action": approval.requested_action,
                "executed_requested_action": requested_action,
            },
        }
        return self._prepare_continuation_request(
            project=project,
            original_request=original_request,
            artifacts=artifacts,
            operator_id=original_request.get("operator_id") or self._config.operator_id,
            requested_action=requested_action,
            human_instruction=human_instruction,
            approval=approval,
        )

    def prepare_continuation_request(
        self,
        *,
        project: ProjectRecord,
        original_request: dict[str, Any],
        artifacts: list[dict[str, Any]],
        operator_id: str | None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        return self._prepare_continuation_request(
            project=project,
            original_request=original_request,
            artifacts=artifacts,
            operator_id=operator_id or self._config.operator_id,
            requested_action="continue",
            human_instruction=None,
            approval=None,
        )

    def _prepare_continuation_request(
        self,
        *,
        project: ProjectRecord,
        original_request: dict[str, Any],
        artifacts: list[dict[str, Any]],
        operator_id: str,
        requested_action: str,
        human_instruction: dict[str, Any] | None,
        approval: ApprovalRequestRecord | None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        latest_by_type: dict[str, Any] = {}
        for item in artifacts:
            latest_by_type[item["artifact_type"]] = item["payload"]

        last_chapter_no = self._last_generated_chapter_no(latest_by_type=latest_by_type, approval=approval)
        if requested_action == "continue":
            chapters_completed = last_chapter_no
            target_chapters = last_chapter_no + 1
        else:
            chapters_completed = max(0, last_chapter_no - 1)
            target_chapters = max(1, last_chapter_no)
        request_payload = {
            "user_brief": original_request.get("user_brief") or project.default_user_brief,
            "target_chapters": target_chapters,
            "operator_id": operator_id,
            "quick_mode": original_request.get("quick_mode", False),
            "creative_contract": latest_by_type.get("creative_contract"),
            "story_bible": latest_by_type.get("story_bible"),
            "arc_plan": latest_by_type.get("arc_plan"),
            "canon_state": self._normalize_canon_state_for_followup(
                canon_state=latest_by_type.get("canon_state"),
                chapters_completed=chapters_completed,
            ),
            "writer_playbook": latest_by_type.get("writer_playbook"),
            "chapter_lesson": latest_by_type.get("chapter_lesson"),
            "issue_ledger": latest_by_type.get("issue_ledger"),
            "chapters_completed": chapters_completed,
        }
        if human_instruction is not None:
            request_payload["human_instruction"] = human_instruction
        return request_payload

    @staticmethod
    def _last_generated_chapter_no(*, latest_by_type: dict[str, Any], approval: ApprovalRequestRecord | None) -> int:
        candidates = [
            ((latest_by_type.get("publish_package") or {}).get("chapter_no")),
            ((latest_by_type.get("current_card") or {}).get("chapter_no")),
            ((latest_by_type.get("planning_context") or {}).get("chapter_no")),
            ((latest_by_type.get("drafting_context") or {}).get("chapter_no")),
            ((latest_by_type.get("chapter_lesson") or {}).get("chapter_no")),
            ((latest_by_type.get("feedback_summary") or {}).get("chapter_no")),
            approval.chapter_no if approval else None,
        ]
        for candidate in candidates:
            try:
                value = int(candidate or 0)
            except (TypeError, ValueError):
                value = 0
            if value > 0:
                return value
        return 0

    @staticmethod
    def _normalize_canon_state_for_followup(*, canon_state: dict[str, Any] | None, chapters_completed: int) -> dict[str, Any]:
        base = dict(canon_state or {})
        story_clock = dict(base.get("story_clock") or {})
        current_chapter = int(story_clock.get("current_chapter") or 0)
        if chapters_completed > current_chapter:
            story_clock["current_chapter"] = chapters_completed
        story_clock.setdefault("current_arc", 1)
        story_clock.setdefault("in_story_time", "day_0")
        base["story_clock"] = story_clock
        base.setdefault("character_states", {})
        base.setdefault("open_loops", [])
        return base

    def run_followup(
        self,
        *,
        project: ProjectRecord,
        request_payload: dict[str, Any],
        on_update=None,
    ) -> dict[str, Any]:
        return self._run_graph(
            input_state={
                "user_brief": request_payload["user_brief"],
                "creative_contract": request_payload["creative_contract"],
                "story_bible": request_payload["story_bible"],
                "arc_plan": request_payload["arc_plan"],
                "canon_state": request_payload["canon_state"],
                "writer_playbook": request_payload.get("writer_playbook"),
                "chapter_lesson": request_payload.get("chapter_lesson"),
                "issue_ledger": request_payload.get("issue_ledger"),
                "human_instruction": request_payload.get("human_instruction"),
                "target_chapters": request_payload["target_chapters"],
                "chapters_completed": request_payload["chapters_completed"],
            },
            context=RuntimeContext(
                project_id=project.project_id,
                operator_id=request_payload["operator_id"],
                model_name=self._config.model_name,
                model_provider="openai",
                openai_base_url=self._config.openai_base_url,
            ),
            on_update=on_update,
        )

    @staticmethod
    def _run_graph(
        *,
        input_state: dict[str, Any],
        context: RuntimeContext,
        on_update=None,
    ) -> dict[str, Any]:
        latest_state: dict[str, Any] = {}
        current_node: str | None = None
        for mode, payload in graph.stream(input_state, context=context, stream_mode=["updates", "values"]):
            if mode == "updates":
                current_node = next(iter(payload.keys()), None)
                continue

            latest_state = payload
            if on_update is not None:
                on_update(current_node, payload)
        return latest_state
