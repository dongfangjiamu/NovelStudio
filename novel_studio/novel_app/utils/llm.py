from __future__ import annotations

import json
import logging
import os
from typing import Any, Callable, TypeVar

from openai import OpenAI
from pydantic import BaseModel

from novel_app.config import parse_bool

from .prompt_loader import load_prompt


T = TypeVar("T")
LOGGER = logging.getLogger(__name__)


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


def _resolve_timeout_seconds(runtime_context: Any) -> float:
    value = (
        getattr(runtime_context, "llm_timeout_seconds", None)
        or os.getenv("NOVEL_STUDIO_LLM_TIMEOUT_SECONDS")
        or "120"
    )
    return float(value)


def _resolve_structured_retry_count(runtime_context: Any) -> int:
    value = (
        getattr(runtime_context, "structured_retry_count", None)
        or os.getenv("NOVEL_STUDIO_STRUCTURED_RETRY_COUNT")
        or "1"
    )
    return max(0, int(value))


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
        "- Keep every string concise and directly useful.\n"
        "- Keep list items short; avoid long narration inside a single field.\n"
        "- Avoid unescaped double quotes inside JSON string values.\n"
        f"- The JSON must conform to this schema:\n{json.dumps(schema_json, ensure_ascii=False, indent=2)}\n\n"
        f"Payload:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )


def _build_retry_user_prompt(*, original_user_text: str, attempt_no: int, error_message: str) -> str:
    return (
        f"{original_user_text}\n\n"
        "The previous answer was invalid JSON and could not be parsed.\n"
        f"Attempt: {attempt_no}\n"
        f"Parsing error: {error_message}\n\n"
        "Retry instructions:\n"
        "- Regenerate the full answer from scratch.\n"
        "- Return exactly one valid JSON object.\n"
        "- Keep field values shorter and more compact than before.\n"
        "- Ensure every quote, bracket, and brace is closed.\n"
        "- Do not include commentary, markdown fences, or trailing text.\n"
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
    elif object_start != -1:
        candidates.append(stripped[object_start:].strip())

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


def _request_output_text(*, client: OpenAI, runtime_context: Any, user_text: str) -> str:
    with client.responses.stream(
        model=_resolve_model_name(runtime_context),
        input=_build_input_items(user_text),
        store=False,
        max_output_tokens=4096,
    ) as stream:
        response = stream.get_final_response()

    return response.output_text or ""


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
        timeout=_resolve_timeout_seconds(runtime_context),
        max_retries=1,
    )
    base_user_text = _build_user_prompt(prompt_name=prompt_name, schema_cls=schema_cls, payload=payload)
    retry_count = _resolve_structured_retry_count(runtime_context)
    last_error: ValueError | None = None

    for attempt_no in range(retry_count + 1):
        user_text = base_user_text
        if attempt_no > 0 and last_error is not None:
            user_text = _build_retry_user_prompt(
                original_user_text=base_user_text,
                attempt_no=attempt_no + 1,
                error_message=str(last_error),
            )

        output_text = _request_output_text(client=client, runtime_context=runtime_context, user_text=user_text)
        try:
            return _parse_structured_text(schema_cls, output_text)
        except ValueError as exc:
            last_error = exc
            LOGGER.warning(
                "Structured response parse failed for %s on attempt %s/%s",
                prompt_name,
                attempt_no + 1,
                retry_count + 1,
            )

    raise ValueError(f"Structured response parsing failed after {retry_count + 1} attempts: {last_error}")
