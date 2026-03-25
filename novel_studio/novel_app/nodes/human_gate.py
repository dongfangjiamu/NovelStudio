from __future__ import annotations

from typing import Any

from novel_app.state import NovelState


def human_gate(state: NovelState, runtime: Any = None) -> dict:
    return {
        "blockers": ["需要人工审核或继续指令。"],
        "event_log": ["human_gate_reached"],
    }
