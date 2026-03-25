from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProjectConfig(StrictModel):
    working_title: str
    platform: str
    genre: str
    chapter_words_target: int = 3000
    total_words_target: int = 1_200_000
    update_cadence: str = "daily"


class ReaderPromise(StrictModel):
    one_sentence_hook: str
    primary_selling_points: list[str] = Field(default_factory=list)


class ControlPanel(StrictModel):
    pacing: int = Field(ge=1, le=5, default=4)
    payoff_density: int = Field(ge=1, le=5, default=4)
    romance_weight: int = Field(ge=1, le=5, default=2)
    prose_flourish: int = Field(ge=1, le=5, default=2)


class NonNegotiables(StrictModel):
    must_have: list[str] = Field(default_factory=list)
    must_not_have: list[str] = Field(default_factory=list)


class CreativeContract(StrictModel):
    project: ProjectConfig
    reader_promise: ReaderPromise
    control_panel: ControlPanel
    non_negotiables: NonNegotiables
    blockers: list[str] = Field(default_factory=list)


class CharacterCard(StrictModel):
    character_id: str
    role: str
    desire: str
    fear: str
    voiceprint: str


class StoryBible(StrictModel):
    premise: str
    world_rules: list[str] = Field(default_factory=list)
    factions: list[str] = Field(default_factory=list)
    character_cards: list[CharacterCard] = Field(default_factory=list)
    fixed_terms: list[str] = Field(default_factory=list)
    red_lines: list[str] = Field(default_factory=list)


class ArcPlan(StrictModel):
    arc_name: str
    arc_goal: str
    conflict_core: str
    milestones: list[str] = Field(default_factory=list)
    foreshadowing: list[str] = Field(default_factory=list)
    climax_hook: str


class EntryState(StrictModel):
    required_context: list[str] = Field(default_factory=list)
    emotional_state: str = "tense"
    unresolved_threads: list[str] = Field(default_factory=list)


class SceneBeat(StrictModel):
    goal: str
    conflict: str
    turn: str


class ChapterHook(StrictModel):
    chapter_end_question: str
    target_reader_impulse: str = "must_click_next"


class ChapterCard(StrictModel):
    chapter_no: int = Field(ge=1)
    purpose: str
    pov: str
    entry_state: EntryState
    scene_beats: list[SceneBeat] = Field(min_length=2)
    must_include: list[str] = Field(default_factory=list)
    must_not_change: list[str] = Field(default_factory=list)
    hook: ChapterHook
    word_count_target: int = Field(ge=1500, default=3000)


class CanonDelta(StrictModel):
    character_updates: list[dict[str, Any]] = Field(default_factory=list)
    world_updates: list[dict[str, Any]] = Field(default_factory=list)
    loop_updates: list[dict[str, Any]] = Field(default_factory=list)


class ChapterDraft(StrictModel):
    title: str
    summary_100w: str
    content: str
    canon_delta_candidate: CanonDelta
    risk_notes: list[str] = Field(default_factory=list)


class ReviewIssue(StrictModel):
    severity: Literal["critical", "major", "minor"]
    type: str
    evidence: str
    fix_instruction: str


class ReviewScores(StrictModel):
    continuity: int = Field(ge=0, le=100)
    pacing: int = Field(ge=0, le=100)
    style: int = Field(ge=0, le=100)
    hook: int = Field(ge=0, le=100)
    total: int = Field(ge=0, le=100)


class ReviewReport(StrictModel):
    reviewer: Literal["continuity", "pacing", "style", "reader_sim"]
    decision: Literal["pass", "rewrite", "replan", "human_review"]
    scores: ReviewScores
    hard_violations: list[str] = Field(default_factory=list)
    issues: list[ReviewIssue] = Field(default_factory=list)


class PhaseDecision(StrictModel):
    final_decision: Literal["pass", "rewrite", "replan", "human_check"]
    must_fix: list[str] = Field(default_factory=list)
    can_defer: list[str] = Field(default_factory=list)
    next_owner: Literal["release_prepare", "patch_writer", "chapter_planner", "human_gate"]
    reason: str


class CanonUpdate(StrictModel):
    chapter_no: int
    character_updates: list[dict[str, Any]] = Field(default_factory=list)
    world_updates: list[str] = Field(default_factory=list)
    loop_updates: list[dict[str, Any]] = Field(default_factory=list)
    summary_150: str


class PublishPackage(StrictModel):
    chapter_no: int
    title: str
    blurb: str
    excerpt: str
