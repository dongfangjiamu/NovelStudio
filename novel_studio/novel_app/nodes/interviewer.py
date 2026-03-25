from __future__ import annotations

from typing import Any

from novel_app.schemas import CreativeContract
from novel_app.state import NovelState
from novel_app.utils.llm import invoke_structured


def _stub_contract(state: NovelState) -> CreativeContract:
    brief = state.get("user_brief") or {}
    return CreativeContract(
        project={
            "working_title": brief.get("title", "未命名项目"),
            "platform": brief.get("platform", "起点中文网"),
            "genre": brief.get("genre", "东方玄幻"),
            "chapter_words_target": brief.get("chapter_words_target", 3000),
            "total_words_target": brief.get("total_words_target", 1_200_000),
            "update_cadence": brief.get("update_cadence", "daily"),
        },
        reader_promise={
            "one_sentence_hook": brief.get(
                "hook",
                "一个被压在底层的年轻人，靠一点危险的秘密逐步撬开整个世界的隐秘结构。",
            ),
            "primary_selling_points": brief.get(
                "selling_points",
                ["强钩子", "稳定升级", "中后期大世界展开"],
            ),
        },
        control_panel={
            "pacing": brief.get("pacing", 4),
            "payoff_density": brief.get("payoff_density", 4),
            "romance_weight": brief.get("romance_weight", 2),
            "prose_flourish": brief.get("prose_flourish", 2),
        },
        non_negotiables={
            "must_have": brief.get("must_have", ["章末钩子", "主角能动性"]),
            "must_not_have": brief.get("must_not_have", ["设定随意破例"]),
        },
        blockers=[],
    )


def interviewer_contract(state: NovelState, runtime: Any = None) -> dict:
    payload = {"user_brief": state.get("user_brief", {})}
    runtime_context = getattr(runtime, "context", None)
    contract = invoke_structured(
        prompt_name="interviewer",
        schema_cls=CreativeContract,
        payload=payload,
        runtime_context=runtime_context,
        stub_factory=lambda: _stub_contract(state),
    )
    return {
        "creative_contract": contract,
        "event_log": ["creative_contract_ready"],
    }
