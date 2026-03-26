from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from novel_app.utils import llm


class DemoSchema(BaseModel):
    title: str
    count: int


def test_invoke_structured_returns_stub_in_stub_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NOVEL_STUDIO_STUB_MODE", "true")

    result = llm.invoke_structured(
        prompt_name="demo_prompt",
        schema_cls=DemoSchema,
        payload={"x": 1},
        runtime_context=SimpleNamespace(model_name="gpt-5.4", openai_base_url=None),
        stub_factory=lambda: DemoSchema(title="stub", count=1),
    )

    assert result == {"title": "stub", "count": 1}


def test_invoke_structured_uses_responses_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NOVEL_STUDIO_STUB_MODE", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "relay-key")
    monkeypatch.setenv("NOVEL_STUDIO_LLM_TIMEOUT_SECONDS", "123")
    captured: dict[str, object] = {}

    class FakeFinalResponse:
        output_text = '{"title":"live","count":2}'

    class FakeStream:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get_final_response(self):
            return FakeFinalResponse()

    class FakeResponses:
        def stream(self, **kwargs):
            captured["stream_kwargs"] = kwargs
            return FakeStream()

    class FakeOpenAI:
        def __init__(self, *, api_key, base_url=None, timeout=None, max_retries=None):
            captured["api_key"] = api_key
            captured["base_url"] = base_url
            captured["timeout"] = timeout
            captured["max_retries"] = max_retries
            self.responses = FakeResponses()

    monkeypatch.setattr(llm, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(llm, "load_prompt", lambda prompt_name: f"PROMPT::{prompt_name}")

    result = llm.invoke_structured(
        prompt_name="demo_prompt",
        schema_cls=DemoSchema,
        payload={"chapter": 3, "title": "灰烬炉心"},
        runtime_context=SimpleNamespace(model_name="gpt-5.4", openai_base_url="https://relay.example.com/openai"),
        stub_factory=lambda: DemoSchema(title="stub", count=1),
    )

    assert result == {"title": "live", "count": 2}
    assert captured["api_key"] == "relay-key"
    assert captured["base_url"] == "https://relay.example.com/openai"
    assert captured["timeout"] == 123.0
    assert captured["max_retries"] == 1
    stream_kwargs = captured["stream_kwargs"]
    assert stream_kwargs["model"] == "gpt-5.4"
    assert stream_kwargs["store"] is False
    assert stream_kwargs["max_output_tokens"] == 4096
    assert stream_kwargs["input"][0]["content"][0]["type"] == "input_text"
    prompt_text = stream_kwargs["input"][0]["content"][0]["text"]
    assert "PROMPT::demo_prompt" in prompt_text
    assert '"chapter": 3' in prompt_text
    assert '"title"' in prompt_text
    assert '"count"' in prompt_text


def test_invoke_structured_raises_when_output_is_not_parsed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NOVEL_STUDIO_STUB_MODE", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "relay-key")

    class FakeFinalResponse:
        output_text = "not-json"

    class FakeStream:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get_final_response(self):
            return FakeFinalResponse()

    class FakeResponses:
        def stream(self, **kwargs):
            return FakeStream()

    class FakeOpenAI:
        def __init__(self, *, api_key, base_url=None, timeout=None, max_retries=None):
            self.responses = FakeResponses()

    monkeypatch.setattr(llm, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(llm, "load_prompt", lambda prompt_name: f"PROMPT::{prompt_name}")

    with pytest.raises(ValueError, match="Structured response parsing failed"):
        llm.invoke_structured(
            prompt_name="demo_prompt",
            schema_cls=DemoSchema,
            payload={"chapter": 3},
            runtime_context=SimpleNamespace(model_name="gpt-5.4", openai_base_url=None),
            stub_factory=lambda: DemoSchema(title="stub", count=1),
        )
