---
name: webnovel-room
description: 多角色中文网文写作工作流，用于立项、设定、分卷大纲、章节卡、正文起草、连贯性审校、追更节奏优化和续写。use when chatgpt needs to help plan, draft, continue, revise, or package a chinese web novel, serial fiction, or long-form story with persistent bible files, role-based collaboration, chapter hooks, and consistency checks.
---

# Webnovel Room

## Overview

Use this skill as a lightweight editorial room for Chinese web novels. Keep a persistent project kit, produce one artifact per stage, and do not jump straight to draft chapters before the upstream planning artifacts exist.

## Default operating rules

1. Treat the story as a serial product. Optimize for hook, retention, clarity, escalation, and recoverable continuity, not for literary opacity.
2. Keep one source of truth for premise, world rules, character cards, timeline, arc outline, foreshadow ledger, and chapter cards.
3. When information is missing, make grounded defaults and label them as defaults instead of blocking.
4. Prefer short artifact cycles: brief -> bible -> arc -> chapter card -> draft -> QA -> polish.
5. For long-running works, update the source-of-truth files after every material plot change.

## Entry decision

Determine which path fits the user request:

- **New project**: the user wants to start a novel, choose a premise, build a workflow, or generate reusable files.
- **Continue serial**: the user already has a setting, outline, or previous chapters and wants the next volume or chapter.
- **Revise / diagnose**: the user wants stronger pacing, better hooks, consistency repair, or style cleanup.
- **Package / scaffold**: the user wants a downloadable folder of templates. Run `scripts/init_project.py`.

## New project workflow

1. Establish the product brief:
   - title or working title
   - genre and subgenre
   - target audience
   - monetization mode or serial cadence if relevant
   - core selling points, taboo elements, desired ending feel
2. Create or update these files in order:
   - `00-project-brief.md`
   - `01-genre-positioning.md`
   - `02-world-bible.md`
   - `03-character-cards.md`
   - `04-arc-outline.md`
   - `05-foreshadow-ledger.md`
   - `06-timeline.md`
3. Before drafting prose, generate `07-chapter-card.md` for the immediate next chapter.
4. Draft the chapter using only the approved chapter card plus existing source files.
5. Run continuity and reader-value checks using `references/quality-checks.md`.
6. Revise once for structure and once for voice. Avoid infinite polishing.

## Continue serial workflow

1. Read the user's latest summary, outline, or chapter text.
2. Reconstruct or refresh the missing source files first. Never continue blind if the continuity load is high.
3. Update timeline and foreshadow ledger before outlining the next chapter.
4. Write one chapter at a time unless the user explicitly requests a block.
5. End each chapter with a tail hook that creates a concrete question, threat, reveal, or reversal.

## Revise / diagnose workflow

1. Identify the dominant problem:
   - weak hook
   - slow pacing
   - exposition dump
   - flat protagonist drive
   - weak conflict ladder
   - broken world rules
   - inconsistent voice
2. Produce a diagnostic note with:
   - symptom
   - cause
   - minimal fix
   - structural fix
3. Apply the fix at the highest leverage level first: brief or arc before chapter, chapter before sentence.

## Role handoff contract

Use these roles sequentially. One assistant may play multiple roles, but the deliverable must be explicit.

1. Chief editor -> defines market position, promise, scope.
2. World builder -> defines rules, factions, costs, maps, taboo boundaries.
3. Character designer -> defines drives, masks, secrets, growth arc, relationship graph.
4. Plot architect -> defines volume goal, midpoint, climax, reversals, payoff plan.
5. Chapter planner -> writes the chapter card with beats, conflict steps, reveal timing, and tail hook.
6. Drafter -> writes prose from the chapter card.
7. Continuity editor -> checks facts, time, power scale, wounds, items, promises.
8. Reader simulator -> scores 爽点, 节奏, 代入, 追更欲 and gives exact fixes.
9. Style editor -> removes repetition, explanation tone, and generic AI phrasing.

See `references/role-cards.md` for details and `references/workflow.md` for artifact flow.

## Output conventions

- Default to Chinese unless the user requests another language.
- Prefer markdown headings and compact tables only when they clearly help.
- For planning artifacts, use the templates in `assets/project-kit/`.
- For diagnosis, use the rubric in `references/quality-checks.md`.
- For chapter cards and revision notes, use the formats in `references/templates.md`.

## File scaffold

When the user asks for a reusable folder, initialize it by running:

```bash
python scripts/init_project.py --title "作品名" --out /mnt/data/novel-project
```

Optional parameters:

- `--genre`
- `--audience`
- `--author`
- `--zip`

Return the created folder or zip if the user wants a download.

## Guardrails

- Do not invent major canon changes silently. Flag them as retcons.
- Do not resolve a high-stakes conflict through coincidence unless the user explicitly wants that mode.
- Do not let any chapter exist only to explain. Every chapter must change status, knowledge, leverage, or emotion.
- Do not overwrite the user's existing canon unless the user asks for a reboot.

## Quick triggers

Good matches for this skill:

- “帮我搭一套网文写作工作流”
- “给这本书做世界观 bible 和人物卡”
- “继续写下一章，但先做章节卡”
- “检查这十章有没有设定打架”
- “给我一个可复用的网文项目模板包”
