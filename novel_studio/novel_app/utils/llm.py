from __future__ import annotations

import json
import os
from typing import Any, Callable, TypeVar

from .prompt_loader import load_prompt


T = TypeVar("T")


def stub_mode_enabled() -> bool:
    return os.getenv("NOVEL_STUDIO_STUB_MODE", "true").lower() in {"1", "true", "yes", "on"}


def _to_dict(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    raise TypeError(f"Unsupported structured output type: {type(value)!r}")


def invoke_structured(
    *,
    prompt_name: str,
    schema_cls: type[T],
    payload: dict,
    runtime_context: Any,
    stub_factory: Callable[[], T | dict],
) -> dict:
    if stub_mode_enabled():
        return _to_dict(stub_factory())

    from langchain_openai import ChatOpenAI

    kwargs: dict[str, Any] = {
        "model": getattr(runtime_context, "model_name", os.getenv("NOVEL_STUDIO_MODEL", "gpt-5-nano")),
    }
    llm = ChatOpenAI(**kwargs)
    runnable = llm.with_structured_output(schema_cls)
    result = runnable.invoke(
        [
            ("system", load_prompt(prompt_name)),
            ("human", json.dumps(payload, ensure_ascii=False, indent=2)),
        ]
    )
    return _to_dict(result)
