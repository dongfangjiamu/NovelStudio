from novel_app.routers import route_after_feedback, route_after_review


def test_route_after_review_pass() -> None:
    assert route_after_review({"phase_decision": {"final_decision": "pass"}}) == "release_prepare"


def test_route_after_review_rewrite() -> None:
    assert route_after_review({"phase_decision": {"final_decision": "rewrite"}}) == "patch_writer"


def test_route_after_review_default() -> None:
    assert route_after_review({}) == "human_gate"


def test_route_rewrite_exceeds_max() -> None:
    state = {
        "phase_decision": {"final_decision": "rewrite"},
        "rewrite_count": 3,
    }
    assert route_after_review(state) == "human_gate"


def test_route_rewrite_within_limit() -> None:
    state = {
        "phase_decision": {"final_decision": "rewrite"},
        "rewrite_count": 2,
    }
    assert route_after_review(state) == "patch_writer"


def test_route_after_feedback_continues() -> None:
    state = {"target_chapters": 3, "chapters_completed": 1}
    assert route_after_feedback(state) == "chapter_planner"


def test_route_after_feedback_ends() -> None:
    state = {"target_chapters": 2, "chapters_completed": 2}
    assert route_after_feedback(state) == "__end__"


def test_route_after_feedback_default_single_chapter() -> None:
    state = {"chapters_completed": 1}
    assert route_after_feedback(state) == "__end__"
