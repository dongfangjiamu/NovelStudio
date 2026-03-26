from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from novel_app.nodes.arc_planner import arc_planner
from novel_app.nodes.canon_manager import canon_commit
from novel_app.nodes.chapter_planner import chapter_planner
from novel_app.nodes.chief_editor import chief_editor
from novel_app.nodes.feedback import feedback_ingest
from novel_app.nodes.human_gate import human_gate
from novel_app.nodes.interviewer import interviewer_contract
from novel_app.nodes.lore_builder import lore_builder
from novel_app.nodes.release import release_prepare
from novel_app.nodes.reviewers import (
    continuity_reviewer,
    pacing_reviewer,
    reader_simulator,
    style_reviewer,
)
from novel_app.nodes.writer import draft_writer, patch_writer
from novel_app.routers import route_after_feedback, route_after_review
from novel_app.state import InputState, NovelState, OutputState, RuntimeContext


builder = StateGraph(
    NovelState,
    input_schema=InputState,
    output_schema=OutputState,
    context_schema=RuntimeContext,
)

builder.add_node("interviewer_contract", interviewer_contract)
builder.add_node("lore_builder", lore_builder)
builder.add_node("arc_planner", arc_planner)
builder.add_node("chapter_planner", chapter_planner)
builder.add_node("draft_writer", draft_writer)
builder.add_node("continuity_reviewer", continuity_reviewer)
builder.add_node("pacing_reviewer", pacing_reviewer)
builder.add_node("style_reviewer", style_reviewer)
builder.add_node("reader_simulator", reader_simulator)
builder.add_node("chief_editor", chief_editor)
builder.add_node("patch_writer", patch_writer)
builder.add_node("release_prepare", release_prepare)
builder.add_node("canon_commit", canon_commit)
builder.add_node("feedback_ingest", feedback_ingest)
builder.add_node("human_gate", human_gate)

builder.add_edge(START, "interviewer_contract")
builder.add_edge("interviewer_contract", "lore_builder")
builder.add_edge("lore_builder", "arc_planner")
builder.add_edge("arc_planner", "chapter_planner")
builder.add_edge("chapter_planner", "draft_writer")

for reviewer in [
    "continuity_reviewer",
    "pacing_reviewer",
    "style_reviewer",
    "reader_simulator",
]:
    builder.add_edge("draft_writer", reviewer)
    builder.add_edge("patch_writer", reviewer)
    builder.add_edge(reviewer, "chief_editor")

builder.add_conditional_edges("chief_editor", route_after_review)
builder.add_edge("release_prepare", "canon_commit")
builder.add_edge("canon_commit", "feedback_ingest")
builder.add_conditional_edges(
    "feedback_ingest",
    route_after_feedback,
    {
        "chapter_planner": "chapter_planner",
        "__end__": END,
    },
)
builder.add_edge("human_gate", END)

graph = builder.compile()
