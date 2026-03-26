from __future__ import annotations

import json
import os
from typing import Any, Callable, TypeVar

from openai import OpenAI
from pydantic import BaseModel

from novel_app.config import parse_bool

from .prompt_loader import load_prompt


T = TypeVar("T")


def stub_mode_enabled() -> bool:
    return parse_bool(os.getenv("NOVEL_STUDIO_STUB_MODE"), True)


def _to_dict(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    raise TypeError(f"Unsupported structured output type: {type(value)!r}")


def _resolve_model_name(runtime_context: Any) -> str:
    return getattr(runtime_context, "model_name", os.getenv("NOVEL_STUDIO_MODEL", "gpt-5-nano"))


def _resolve_base_url(runtime_context: Any) -> str | None:
    return getattr(runtime_context, "openai_base_url", None) or os.getenv("OPENAI_BASE_URL") or os.getenv(
        "NOVEL_STUDIO_OPENAI_BASE_URL"
    )


def _build_user_prompt(*, prompt_name: str, schema_cls: type[T], payload: dict) -> str:
    schema_json = {}
    if issubclass(schema_cls, BaseModel):
        schema_json = schema_cls.model_json_schema()

    return (
        f"{load_prompt(prompt_name).strip()}\n\n"
        "Output contract:\n"
        "- Return exactly one JSON object.\n"
        "- Do not wrap JSON in markdown fences.\n"
        "- Do not add explanation before or after the JSON.\n"
        f"- The JSON must conform to this schema:\n{json.dumps(schema_json, ensure_ascii=False, indent=2)}\n\n"
        f"Payload:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )


def _build_input_items(user_text: str) -> list[dict[str, Any]]:
    return [
        {
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": user_text,
                }
            ],
        }
    ]


def _parse_structured_text(schema_cls: type[T], text: str) -> dict:
    candidates = [text.strip()]
    stripped = text.strip()
    if stripped.startswith("```"):
        fence_lines = stripped.splitlines()
        if len(fence_lines) >= 3:
            candidates.append("\n".join(fence_lines[1:-1]).strip())

    object_start = stripped.find("{")
    object_end = stripped.rfind("}")
    if object_start != -1 and object_end != -1 and object_end > object_start:
        candidates.append(stripped[object_start : object_end + 1].strip())

    last_error: Exception | None = None
    for candidate in candidates:
        if not candidate:
            continue
        try:
            if issubclass(schema_cls, BaseModel):
                return _to_dict(schema_cls.model_validate_json(candidate))
            return _to_dict(json.loads(candidate))
        except Exception as exc:  # pragma: no cover - exercised through aggregate failure path
            last_error = exc

    raise ValueError(f"Structured response parsing failed: {last_error}")


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

    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=_resolve_base_url(runtime_context),
    )
    user_text = _build_user_prompt(prompt_name=prompt_name, schema_cls=schema_cls, payload=payload)
    with client.responses.stream(
        model=_resolve_model_name(runtime_context),
        input=_build_input_items(user_text),
        store=False,
        max_output_tokens=4096,
    ) as stream:
        response = stream.get_final_response()

    return _parse_structured_text(schema_cls, response.output_text or "")
