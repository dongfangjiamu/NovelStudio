from novel_app.nodes import reviewers


def test_stub_reviewers_request_rewrite_before_patch() -> None:
    state = {
        "current_draft": {"content": "未修补版本"},
    }

    continuity = reviewers.continuity_reviewer(state)
    pacing = reviewers.pacing_reviewer(state)
    style = reviewers.style_reviewer(state)
    reader_sim = reviewers.reader_simulator(state)

    assert continuity["review_reports"][0]["decision"] == "rewrite"
    assert pacing["review_reports"][0]["decision"] == "rewrite"
    assert style["review_reports"][0]["decision"] == "pass"
    assert reader_sim["review_reports"][0]["decision"] == "rewrite"
    assert continuity["event_log"] == ["review_ready:continuity:rewrite"]


def test_stub_reviewers_pass_after_patch() -> None:
    state = {
        "current_draft": {"content": "已经修补\n[PATCHED]"},
    }

    continuity = reviewers.continuity_reviewer(state)
    pacing = reviewers.pacing_reviewer(state)
    reader_sim = reviewers.reader_simulator(state)

    assert continuity["review_reports"][0]["decision"] == "pass"
    assert pacing["review_reports"][0]["decision"] == "pass"
    assert reader_sim["review_reports"][0]["decision"] == "pass"


def test_llm_reviewer_uses_structured_payload(monkeypatch) -> None:
    monkeypatch.setenv("NOVEL_STUDIO_STUB_MODE", "false")
    captured: dict[str, object] = {}

    def fake_invoke_structured(**kwargs):
        captured.update(kwargs)
        return {
            "reviewer": "continuity",
            "decision": "human_review",
            "scores": {"continuity": 60, "pacing": 70, "style": 75, "hook": 65, "total": 68},
            "hard_violations": [],
            "issues": [
                {
                    "severity": "major",
                    "type": "canon",
                    "evidence": "test",
                    "fix_instruction": "补充证据链",
                }
            ],
        }

    monkeypatch.setattr(reviewers, "invoke_structured", fake_invoke_structured)

    state = {
        "creative_contract": {"project": {"working_title": "x"}},
        "story_bible": {"premise": "y"},
        "arc_plan": {"arc_name": "z"},
        "canon_state": {"story_clock": {"current_chapter": 1}},
        "current_card": {"chapter_no": 2},
        "current_draft": {"title": "第2章"},
    }
    result = reviewers.continuity_reviewer(state)

    assert captured["prompt_name"] == "continuity_reviewer"
    assert captured["schema_cls"].__name__ == "ReviewReport"
    assert captured["payload"]["reviewer"] == "continuity"
    assert captured["payload"]["current_draft"]["title"] == "第2章"
    assert result["review_reports"][0]["decision"] == "human_review"
    assert result["event_log"] == ["review_ready:continuity:human_review"]
