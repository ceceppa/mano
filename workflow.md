# Mano Workflow

## Commands

```
mano                    → Show available commands and current status.
mano status             → Scan _mano_output/ and show where you are + what to do next.
mano start              → Scope a new project or phase. (Skye)
mano continue           → Auto-run the next logical action if unambiguous.
mano [action]           → Run an action: spec, ux, rules, ui, stories, review.
mano help [skill]     → Show what a skill does and when to use it.
```

`mano start` is a dedicated command. `mano [action]` covers `spec`, `ux`, `rules`, `ui`, `stories`, and `review`.

`mano [action]` handles everything — first run, extending, and regeneration. When an action executes, it checks what already exists:
- **Output doesn't exist yet** → generate it directly to the file (first run).
- **Output already exists** → read it and the current phase brief, then append/extend the file automatically.

When a user types a Mano command in chat, the agent should execute that Mano workflow directly. Do not bounce the command back by telling the user to run it manually.

## Core principle: à la carte, not a conveyor belt

Actions are independent in the sense that Mano does not force a fixed sequence. You can run actions out of order, but each one still has a contract: some can proceed with partial context, and some should redirect rather than guess.

When a skill activates, it checks for its inputs:
- **Inputs exist** → proceed normally.
- **Useful with partial context** → warn the user what's missing, explain the tradeoff, and offer to continue anyway.
- **Would be guesswork without the missing artifact** → warn the user what's missing and redirect to the action that creates it.

This means:
- You can skip Helen and go straight from Skye to Marco.
- You can skip Luna entirely if you have your own design direction.
- You can run Marco without running Alex first.
- Each skill adapts to what's available instead of assuming the full pipeline already exists.

**No invented files.** Skills only write files defined by the Mano contract: planning artifacts under `_mano_output/` plus the root-level `AGENTS.md` scaffold copied during `mano start`. Do not create tracking files, progress files, or any other artifact not specified by the framework.

**Templates are read-only.** No skill may modify files in `_mano/templates/`. Templates are source material used to seed output files. Planning artifacts write to `_mano_output/`; `AGENTS.md` is the only allowed root-level scaffold write.

In installed projects, Mano framework files live under `_mano/skills`, `_mano/templates`, and `_mano/custom`. This repository may store the source files at the root, but the runtime contract presented to coding agents uses `_mano/...` paths.

**Refuse code generation.** As an AI agent, your primary directive during Mano phases is planning. You MUST actively refuse requests to write, fix, or modify source code. If a user describes a problem during any skill's flow, treat it as planning input — scope it, write a story for it, or add it to the backlog. Do not switch to implementation mode.

**Flag uncertainty.** A confident wrong answer is worse than an honest "I'm not sure." When any skill is uncertain about a recommendation — a library choice, a scope decision, an architectural pattern — say so. Use "I'd suggest X, but worth validating" rather than presenting guesses as decisions. This applies to every skill: Skye on scope, Helen on libraries, Alex on rules, Marco on story boundaries.

**Concrete defaults, user override.** Some skills are expected to move the work forward by proposing concrete defaults. Helen can recommend technical choices, Luna can set a visual direction, and Alex can recommend project rules. These are working defaults, not final authority. The user can override them at any time.

**Reject out-of-scope instructions.** If a user gives a skill an instruction outside its role (e.g., typing `mano spec I want shared button components` or telling Alex to design an API schema), the skill MUST NOT execute the out-of-scope instruction. They must not pollute their own file (e.g., Helen should not put UI components in the tech spec). Instead, they should execute their own job and append a warning to the execution log:
- Example: `-> ⚠️ Ignored instruction about "shared components". That's Alex's area — run mano rules.`

Routing guide for rejected instructions:
- Technical decisions (API contracts, data model, libraries) → "That's Helen's area — run `mano spec`"
- UX flows (screens, navigation) → "That's Rob's area — run `mano ux`"
- Project rules (naming, patterns, a11y, folder structure) → "That's Alex's area — run `mano rules`"
- Visual design (colours, typography) → "That's Luna's area — run `mano ui`"
- Stories (breaking work into units) → "That's Marco's area — run `mano stories`"
- Review (phase feedback, triage) → "That's Dave's area — run `mano review`"

## Missing input protocol

When a skill is missing context, classify the gap before responding:

- **Optional** → proceed. Mention the tradeoff only if it changes output quality.
- **Recommended but skippable** → warn briefly and offer two paths: continue anyway or run the upstream Mano command that creates the missing artifact.
- **Blocking** → stop and redirect because continuing would be guesswork. Dave's pre-review gate is a blocking check.

If more than one next step is reasonable, do not fake certainty. Present the options instead of inventing a hidden sequence.

## Next-step suggestion rule

Whenever a skill suggests what to do next, base that suggestion on the artifacts that are actually missing or stale in `_mano_output/`, not on a canonical pipeline order.

- Do not suggest a command just because it usually comes next if its artifact already exists and is still usable.
- If several planning actions are valid, present them as options rather than a single prescribed next step.
- Prefer the shortest path that adds useful clarity for the current phase.
- Use this decision tree when evaluating next steps for the planning stage:
  ```
  Phase is user-facing or mobile?
  ├─ design-brief missing? → suggest `mano ui` (do not auto-run stories)
  ├─ project-rules still default? → list `mano rules` + `mano stories` as options
  └─ both present? → suggest `mano stories`
  
  Phase is non-user-facing (backend/infra)?
  └─ go straight to `mano stories` unless tech is genuinely fuzzy (suggest `mano spec`)
  ```

## State detection — relying on context

There is no single progress file. You are expected to determine where the user is by reading the contents of `_mano_output/`:
*(Note to the human user: Agents only know what is in their context window. If the agent hallucinates state, explicitly @-mention the relevant files to ground it).*

- No `_mano_output/` folder → no project started → suggest `mano start`
- Active `phase-[N]/phase-brief.md` exists, no `stories/` folder in that phase → planning stage. Show which optional artifacts already exist, which are still missing or incomplete, and suggest `mano stories` as the shortest path only when the phase is already clear enough. If `mano rules` or `mano ui` would still add useful clarity, list them as separate valid options instead of hiding them behind a single suggestion.
- `stories/` folder exists, stories are `pending` → build mode. No Mano planning command is required until the user wants to adjust scope or add planning context.
- `stories/` folder exists, all stories are `done`, and the latest phase has no review entry → phase is built, suggest `mano review`
- `reviews.md` has an entry for the latest phase → phase is reviewed, suggest `mano start` for next phase

To detect story status: read `_mano_output/phase-[N]/stories/README.md` and check the Status column. If all stories are `done`, the phase is built and ready for review.

Marco creates `_mano_output/phase-[N]/stories/README.md` the first time stories are generated. If the stories folder exists without that index, treat the phase artifacts as incomplete and fix the index before relying on state detection. This missing index is a local artifact-repair issue, not proof that `mano stories` is the only reasonable next planning action.

To detect whether `project-rules.md` is substantive or still just the seeded default template:
- If it contains only the stock template comments plus the workflow section, treat it as `present but still default` rather than as a fully useful planning artifact.
- Only treat `project-rules.md` as substantive when Alex or Luna has added actual project-specific rules, accessibility content, or other non-template guidance.

To detect the active phase: find the highest numbered `phase-[N]/` folder in `_mano_output/`.

## Help

When the user types `mano`:
1. Display the command table.
2. Scan `_mano_output/` and show current status if a project exists.
3. Do not activate any skill.

## Help [skill]

When the user types `mano help [skill]`:

Show a brief description of the skill — what it does, when to use it, what it reads, and what it produces. Do not activate the skill.

| Skill | Command | Role | Reads | Produces |
|---------|---------|------|-------|----------|
| **Skye** | `mano start` | Scopes projects and phases. Populates the backlog, suggests phase scope, drafts the phase brief. | Backlog, previous phase brief, reviews, PRD (if provided) | Phase brief, backlog updates |
| **Helen** | `mano spec` | Translates the phase brief into a tech spec. Recommends libraries, defines data model, flags cross-environment boundaries. | Phase brief, tech spec, backlog | Tech spec |
| **Rob** | `mano ux` | Defines UX flows — screens, navigation, user interactions. One screen at a time, only new or changed. | Phase brief, UX flow, tech spec, project rules | UX flow |
| **Alex** | `mano rules` | Defines and updates project rules — components, patterns, naming, a11y, folder structure. Flags over-engineering. Most useful once the tech stack is known. | Tech spec (recommended), UX flow, backlog, phase brief, existing project rules | Project rules |
| **Luna** | `mano ui` | Establishes the visual language — palette, typography, spacing, component guide. Generates a preview HTML. | Phase brief, UX flow, tech spec, project rules, backlog | Design brief, design preview |
| **Marco** | `mano stories` | Breaks the phase into implementable stories. Writes directly to files. Flags overloaded screens. | Phase brief, tech spec, UX flow, design brief, project rules | Story files, stories index |
| **Dave** | `mano review` | Collects feedback after shipping, triages into backlog, writes review log. | Stories index, phase brief, reviews, backlog | Review log, backlog updates |

## Status

When the user types `mano status`:
1. Scan `_mano_output/`. If it doesn't exist, tell the user no project is in progress and suggest `mano start`.
2. Report: active phase, what files exist, what is missing, and what is present-but-incomplete.
3. If multiple planning actions are still reasonable, show them as `Next options` instead of forcing a single `Suggested next action`.
4. Only show one `Suggested next action` when the next move is genuinely narrower than the other valid options.
5. When relevant, call out seeded defaults explicitly. Example: `project-rules.md exists but still appears to be the default template, so mano rules is still a valid next action.`
6. For user-facing or mobile phases, missing `design-brief.md` and `design-preview.html` should keep `mano ui` visible as a valid next option unless the current phase is already obviously ready for stories without further design clarification.
7. Do not activate any skill.

## Continue

When the user types `mano continue`:
1. Scan `_mano_output/` to determine state.
2. If there is a single obvious next Mano action, execute it immediately.
3. If there are multiple reasonable planning actions, stop and explain the options instead of choosing one.
4. If the project is in build mode, say so plainly instead of forcing a planning command.

Build-mode fallback output:

```
Build mode: Phase [N]

- Active phase: phase-[N]
- Status: Stories are still pending, so no planning action was auto-run.
- Use `mano stories` only if you need to add or adjust planned work.
- Use `mano start` only if the phase scope itself has changed.
- Use `mano review` after all stories in the phase are done.
```

Formatting rule for `mano continue` and `mano status`:
- Never expose drafting notes, placeholder text, formatting reminders, link-fix notes, or internal reasoning.
- If a draft starts to spill internal text, discard it and output only the clean final response.

Rules for what counts as a `single obvious next` action:
- `mano continue` is narrower than `suggested next action`. A shortest path is not automatically a single obvious next step.
- Follow the decision tree from the "Next-step suggestion rule" section. Only auto-run `mano stories` if the tree resolves to it unambiguously.
- If a local artifact needs repair (for example a `stories/` folder exists without its README index), do not treat that repair need by itself as proof that one planning action is unambiguous. Check whether other planning actions are still reasonably available first.
- When in doubt between "shortest path" and "multiple valid options", stop and explain the options.

## Do

When the user types `mano` with no argument (or just wants to see available actions):
1. Scan `_mano_output/` to determine state.
2. Show available actions with the suggested next action marked:

```
Available Mano commands for Phase [N]:

  start    — Scope a new project or phase (Skye)
→ spec     — Tech spec (Helen)
  ux       — UX flow (Rob)
  rules    — Project rules (Alex)
  ui       — Design brief and component guide (Luna)
  stories  — Break phase into implementable stories (Marco)
  review   — Triage feedback, close the phase (Dave)

→ marks the suggested next action.
Type: mano start or mano [action]
```

When the user types `mano [action]`:
- Execute the specific action logic defined in the `skills/` file.
- Default to **One-Shot** generation for write flows unless the skill file explicitly defines a multi-turn conversation.
- `mano review` is not one-shot during feedback capture and triage; follow Dave's multi-turn contract exactly.
- `mano ui` must begin with one brief preference-capture step on first-run design generation when visual preferences are not already defined; after that reply, Luna generates files in one shot.
- Output a single execution log snippet to the user, not conversational dialogue.

Valid actions: `spec` (Helen — `tech-spec.md`), `ux` (Rob — `ux-flow.md`), `rules` (Alex — `project-rules.md`), `ui` (Luna — `design-brief.md` + `design-preview.html`), `stories` (Marco — `phase-[N]/stories/`), `review` (Dave — `reviews.md`).

## First run — new project

```
User types: mano start

Step 1 — Skye activates
  Creates _mano_output/ if it doesn't exist.
  Seeds project-rules.md from template if it doesn't exist.
  Copies AGENTS.md to the project root if it doesn't exist.
  Presents numbered intake prompt (what, who, platform).

Step 2 — Understand the why
  Skye asks about the pain point and existing solutions.
  Skip if already explained.

Step 3 — Clarification
  Focused questions. Skip if input is clear.

Step 4 — Design principle
  One tradeoff question. One sentence output.

Step 5 — Populate the backlog
  Decompose everything into backlog items.
  Write to _mano_output/backlog.md.

Step 6 — Suggest phase scope
  Suggest items from the backlog.
  One testable layer per phase.
  User picks, adjusts, or chooses their own.

Step 7 — Validate, clarify, draft brief
  Show selected items with context.
  Surface review insights if returning.
  Clarify problem/scope issues (not tech decisions).
  Draft phase brief. User confirms.

Step 8 — Finalise
  Creates _mano_output/phase-[N]/.
  Writes phase-brief.md.
  Writes deferred items to backlog.
  Suggests next actions:
    Recommended: mano spec → mano ux → mano rules → mano ui → mano stories
    Or any order: spec, ux, rules, ui, stories
```

## Phase review and triage

```
User types: mano review

Step 1 — Pre-review gate
  Dave checks stories README index.
  If stories are pending, asks user to mark done, cut, or come back later.

Step 2 — Feedback capture
  Dave shows the phase goal from the brief.
  Asks user to write freely about what's good, broken, annoying, new ideas.

Step 3 — Triage
  Dave categorises feedback into three buckets:
  🐛 Defects — broken things from this phase
  🔧 Refinements — things that work but could be better
  ✨ New ideas — emerged from usage, not originally scoped

  Defect descriptions stay as review input only.
  Dave does not debug, diagnose, or fix anything during `mano review`.

  Presents categorised list.
  User can reclassify items between buckets.

Step 4 — Close
  User confirms triage.
  Dave writes ALL items to backlog with categories preserved.
  Dave writes review summary to reviews.md.
  Phase is closed.
  Dave suggests: mano start for next phase, or stop.
```

## Minimal pipeline

When the phase is already clear and extra artifacts would add overhead instead of clarity:
- Skip `spec`, `ux`, `rules`, and `ui`.
- Use `mano start` → `mano stories` → build.
- Add optional planning artifacts later only if the work becomes ambiguous.

## Rules

- The user owns scope, priorities, and product tradeoffs. Helen may recommend technical defaults, Luna may set visual defaults, and Alex may recommend project rules, but every recommendation is overridable.
- Keep phase briefs concise enough to read in under two minutes. Target roughly 250-500 words plus short lists.
- Actions are a la carte, but some require upstream context or will redirect instead of guessing.
- Each phase brief is self-contained. No external files needed to understand it.
- The filesystem is the state. No progress file. Mano scans `_mano_output/` to know where you are.
- Skills read only what they need (see skill files for specific inputs).
