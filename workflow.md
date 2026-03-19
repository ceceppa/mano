# Mano Workflow

## Commands

```
mano              → Show available commands and current status.
mano-status       → Scan _mano_output/ and show where you are + what to do next.
mano-start        → Scope a new project or phase. (Skye, optionally Alex)
mano-continue     → Auto-run the next logical action if unambiguous.
mano-do [action]  → Run an action: spec, ui, stories, review.
mano-ask [action] → Chat with a persona about their output.
mano-redo [action] → Regenerate a persona's output from scratch.
```

## Core principle: à la carte, not a conveyor belt

Actions are independent. Any action works at any time if its inputs exist. No action refuses to run because a previous step was skipped.

When a persona activates, it checks for its inputs:
- **Inputs exist** → proceed normally.
- **Inputs missing** → warn the user what's missing, ask if they want to continue anyway or go back.

This means:
- You can skip Helen and go straight from Skye to Marco.
- You can skip Mia entirely if you have your own design direction.
- You can run Marco without Alex having challenged the brief.
- Each persona adapts to what's available, not what the pipeline demands.

## State detection — the filesystem is the truth

There is no progress file. Mano determines where you are by scanning `_mano_output/`:

- No `_mano_output/` folder → no project started → suggest `mano-start`
- `phase-[N]/phase-brief.md` exists, no `tech-spec.md` → suggest `mano-do spec`
- `phase-[N]/tech-spec.md` and `ux-flow.md` exist, no `design-brief.md` → suggest `mano-do ui`
- `design-brief.md` exists, no `stories/` folder → suggest `mano-do stories`
- `stories/` folder exists with stories → in build mode
- All phases have stories, latest was shipped → suggest `mano-do review`

To detect the active phase: find the highest numbered `phase-[N]/` folder in `_mano_output/`.

## Help

When the user types `mano`:
1. Display the command table.
2. Scan `_mano_output/` and show current status if a project exists.
3. Do not activate any persona.

## Status

When the user types `mano-status`:
1. Scan `_mano_output/`. If it doesn't exist, tell the user no project is in progress and suggest `mano-start`.
2. Report: active phase, what files exist, what's missing, and the suggested next action.
3. Do not activate any persona.

## Continue

When the user types `mano-continue`:
1. Scan `_mano_output/` to determine state.
2. If the next action is unambiguous, execute it immediately.
3. If it requires a user decision, stop and explain why.

## Do

When the user types `mano-do` with no argument:
1. Scan `_mano_output/` to determine state.
2. Show available actions with the suggested next action marked:

```
Available actions for Phase [N]:

→ spec     — Generate tech spec and UX flow (Helen)
  ui       — Generate design brief and component guide (Mia)
  stories  — Break phase into implementable stories (Marco)
  review   — Report feedback after shipping, scope next phase

→ marks the suggested next action.
Type: mano-do [action]
```

## Ask

When the user types `mano-ask [action]`:
1. Activate the persona in conversation mode.
2. They discuss, explain, and modify their output without regenerating everything.
3. Only affected parts of output files are updated.

Valid actions: `start`, `challenger`, `spec`, `ui`, `stories`.

## Redo

When the user types `mano-redo [action]`:
1. Regenerate the persona's output from scratch.
2. Overwrites previous output for that persona only.

Valid actions: `spec`, `ui`, `stories`.

## First run — new project

```
User types: mano-start

Step 1 — Skye activates
  Creates _mano_output/ if it doesn't exist.
  Presents numbered intake prompt (what, who, platform).

Step 2 — Understand the why
  Skye asks about the pain point and existing solutions.
  Skip if already explained.

Step 3 — Clarification
  Max three focused questions. Skip if input is clear.

Step 4 — Design principle
  One tradeoff question. One sentence output.

Step 5 — Phase brief draft
  Skye produces self-contained phase brief: problem, vision,
  design principle, weight assessment, tech stack (if known),
  phase scope, exit criteria, assumption log, next phase candidates.
  Must fit one screen.
  User confirms or edits.
  Skye asks: challenge or skip?

Step 6 — Challenge or skip
  Option 1: Challenge → Alex runs (Steps 7-8)
  Option 2: Skip → Skye writes brief directly

Step 7 — Alex audit
  Assumption scores, missing assumptions, scope challenge,
  confidence score, numbered deferral candidates.

Step 8 — Resolution
  Accept / Defer items / Change / Kill

Step 9 — Skye finalises
  Creates _mano_output/phase-[N]/.
  Writes self-contained phase-brief.md.
  Suggests next action (mano-do spec, or mano-do stories for simple projects).
```

## Phase review and triage

```
User types: mano-do review

Step 1 — Feedback capture
  Skye activates. User reports what worked, what didn't,
  what's broken, what's missing, what ideas emerged.

Step 2 — Triage
  Skye categorises feedback into three buckets:
  🐛 Defects — broken things from this phase
  🔧 Refinements — things that work but could be better
  ✨ New ideas — emerged from usage, not originally scoped

  Presents categorised list and options:
  1. Fix defects first (stay in current phase)
  2. Fix defects + refinements (stay in current phase)
  3. Move to next phase (carry everything forward)
  4. Cherry-pick (fix some now, defer the rest)

  User can reclassify items between buckets before deciding.

Step 3a — If staying in current phase (options 1, 2, or 4-fix)
  Marco creates fix stories using sub-numbering (8a, 8b, etc.).
  No specs, no UI, no full pipeline. Just fix stories.
  Deferred items (if any) written to next phase candidates with categories.
  After fixes complete → escape velocity check (Step 4).

Step 3b — If moving to next phase (option 3 or 4-defer)
  ALL items written to next phase candidates with categories preserved.
  Defects stay marked as defects — they don't become optional.
  Proceed to Step 4.

Step 4 — Escape velocity
  Only after fixes are done (or user chose to move on):

  1. 🚀 Light mode — Scope and go straight to stories.
  2. 📋 Full pipeline — Run the complete flow.
  3. 🏁 I'm good — Don't need Mano. Come back if stuck.

Step 5 — Next phase scoping (if not option 3 above)
  Skye copies the previous phase brief as a starting point.
  Includes carried-forward items in candidates list.
  Updates problem/vision/tech stack if feedback requires it.
  Scopes the new phase.
  Challenge or skip.
  Writes new phase-brief.md to _mano_output/phase-[N]/.
```

## Weight-based pipeline collapse

When Skye's weight assessment flags a project as **single deliverable**:
- Skip Alex, Helen, and Mia entirely.
- Skye scopes → Marco writes stories → build.
- Three steps total.

## Rules

- No persona makes decisions. The user decides everything.
- No phase brief exceeds one screen.
- Actions are independent. Skip anything, run anything.
- Each phase brief is self-contained. No external files needed to understand it.
- The filesystem is the state. No progress file. Mano scans `_mano_output/` to know where you are.
- Personas read only what they need (see persona files for specific inputs).
