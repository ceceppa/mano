# Mano Workflow

## Commands

```
mano                    → Show available commands and current status.
mano status             → Scan _mano_output/ and show where you are + what to do next.
mano start              → Scope a new project or phase.
mano continue           → Auto-run the next logical action if unambiguous.
mano [action]           → Run a planning action: spec, ux, rules, ui, stories, review.
mano dev                → Implement the next pending story for the active phase.
mano help [skill]     → Show what a skill does and when to use it.
```

`mano start` is a dedicated command. `mano [action]` covers `spec`, `ux`, `rules`, `ui`, `stories`, and `review`.

**Dispatch only to Mano's own skills — never a similarly-named built-in.** Every `mano <action>` resolves to the matching skill in `_mano/skills/` and to nothing else. The host environment may contain built-in, harness, plugin, or third-party skills whose names overlap a Mano action word — do **not** invoke those for a `mano` command, even if their name looks like an exact match. Resolve the command by its Mano role (the agent and contract below), not by keyword similarity to an ambient skill. Two known, high-impact collisions to call out explicitly:
- **`mano review` → `mano review`** (`_mano/skills/review.md`): collect feedback, triage into the backlog, write the review log, close the phase. It reads **only** Mano artifacts and never inspects source. It is **not** a code review / pull-request review / multi-angle diff review. If you find yourself running `git diff`, scanning the diff for bugs, or launching review *agents*, you have invoked the wrong skill — stop and run `mano review` instead.
- **`mano dev` → the implementer** (`_mano/skills/dev.md` → `AGENTS.md` contract): implement the next pending story. It is **not** a dev server, build/run command, or editor launch. If you find yourself starting a server or opening the project in an editor, you have invoked the wrong skill.

Every Mano skill's exact name is `mano-<action>` (`mano-review`, `mano-dev`, `mano-spec`, …). When a user types the spaced form of a colliding action (`mano review`, `mano dev`), resolve it to that **exact** Mano skill name — the same as if they had typed `mano-review` / `mano-dev` — never to a built-in that merely shares the bare keyword. The hyphenated name matches a Mano skill and no built-in, so it is the unambiguous target; the space is only a friendlier spelling of it. If a user re-issues a command in hyphenated form after a misfire, that is them forcing the exact match — honour it as the Mano skill.

`mano dev` is **not** a planning action — it is the implementation entry point. It does not generate planning artifacts; it implements the next pending story by following the contract in `AGENTS.md`. See `skills/dev.md` (a thin pointer to that contract). The "Refuse code generation" rule below applies to the planning actions, not to `mano dev`.

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
- You can skip `mano spec` and go straight from `mano start` to `mano stories`.
- You can skip `mano ui` entirely if you have your own design direction.
- You can run `mano stories` without running `mano rules` first.
- Each skill adapts to what's available instead of assuming the full pipeline already exists.

**No invented files.** Skills only write files defined by the Mano contract: planning artifacts under `_mano_output/` plus the root-level `AGENTS.md` scaffold copied during `mano start`. Do not create tracking files, progress files, or any other artifact not specified by the framework.

**Templates are read-only.** No skill may modify files in `_mano/templates/`. Templates are source material used to create output files only when the relevant action is explicitly run. Planning artifacts write to `_mano_output/`; `AGENTS.md` is the only allowed root-level scaffold write.

In installed projects, Mano framework files live under `_mano/skills` and `_mano/templates`. This repository may store the source files at the root, but the runtime contract presented to coding agents uses `_mano/...` paths.

**Refuse code generation.** As an AI agent, your primary directive during Mano phases is planning. You MUST actively refuse requests to write, fix, or modify source code. If a user describes a problem during any skill's flow, treat it as planning input — scope it, write a story for it, or add it to the backlog. Do not switch to implementation mode.

**Flag uncertainty.** A confident wrong answer is worse than an honest "I'm not sure." When any skill is uncertain about a recommendation — a library choice, a scope decision, an architectural pattern — say so. Use "I'd suggest X, but worth validating" rather than presenting guesses as decisions. This applies to every skill: `mano start` on scope, `mano spec` on libraries, `mano rules` on rules, `mano stories` on story boundaries.

**Concrete defaults, user override.** Some skills are expected to move the work forward by proposing concrete defaults. `mano spec` can recommend technical choices, `mano ui` can set a visual direction, and `mano rules` can recommend project rules. These are working defaults, not final authority. The user can override them at any time.

**Reject out-of-scope instructions.** If a user gives a skill an instruction outside its role (e.g., typing `mano spec I want shared button components` or telling `mano rules` to design an API schema), the skill MUST NOT execute the out-of-scope instruction. They must not pollute their own file (e.g., `mano spec` should not put UI components in the tech spec). Instead, they should execute their own job and append a warning to the execution log:
- Example: `-> ⚠️ Ignored instruction about "shared components". That's `mano rules`'s area — run mano rules.`

Routing guide for rejected instructions:
- Technical decisions (API contracts, data model, libraries) → "That's `mano spec`'s area — run `mano spec`"
- UX flows (screens, navigation) → "That's `mano ux`'s area — run `mano ux`"
- Project rules (naming, patterns, a11y, folder structure) → "That's `mano rules`'s area — run `mano rules`"
- Visual design (colours, typography) → "That's `mano ui`'s area — run `mano ui`"
- Stories (breaking work into units) → "That's `mano stories`'s area — run `mano stories`"
- Review (phase feedback, triage) → "That's `mano review`'s area — run `mano review`"

## Missing input protocol

When a skill is missing context, classify the gap before responding:

- **Optional** → proceed. Mention the tradeoff only if it changes output quality.
- **Recommended but skippable** → warn briefly and offer two paths: continue anyway or run the upstream Mano command that creates the missing artifact.
- **Blocking** → stop and redirect because continuing would be guesswork. `mano review`'s pre-review gate is a blocking check.

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
- `stories/` folder exists, stories are `pending` → build mode. The next step is implementation: suggest `mano dev` to implement the next pending story. No Mano planning command is required until the user wants to adjust scope or add planning context.
- `stories/` folder exists, all stories are `done`, and the latest phase has no review entry → phase is **built but not closed**. Direct the user to `mano review` — review is mandatory to close a phase, not an optional suggestion. Do not call the phase "complete" and do not offer `mano start` as an equal alternative: `mano start` will refuse to scope the next phase until review moves this phase's backlog items off `in-phase-[N]`.
- `reviews.md` has an entry for the latest phase → phase is reviewed, suggest `mano start` for next phase

To detect story status: read `_mano_output/phase-[N]/stories/README.md` and check the Status column. If all stories are `done`, the phase is built and ready for review.

`mano stories` creates `_mano_output/phase-[N]/stories/README.md` the first time stories are generated. If the stories folder exists without that index, treat the phase artifacts as incomplete and fix the index before relying on state detection. This missing index is a local artifact-repair issue, not proof that `mano stories` is the only reasonable next planning action.

To detect the active phase: find the highest numbered `phase-[N]/` folder in `_mano_output/`.

## Help

When the user types `mano`:
1. Display the command table.
2. Scan `_mano_output/` and show current status if a project exists.
3. Do not activate any skill.

## Help [skill]

When the user types `mano help [skill]`:

Show a brief description of the skill — what it does, when to use it, what it reads, and what it produces. Do not activate the skill.

| Command | Role | Reads | Produces |
|---------|------|-------|----------|
| **`mano start`** | Scopes projects and phases. Populates the backlog, suggests phase scope, drafts the phase brief. | Backlog, previous phase brief, reviews, PRD (if provided) | Phase brief, backlog updates |
| **`mano spec`** | Translates the phase brief into a tech spec. Recommends libraries, defines data model, flags cross-environment boundaries. | Phase brief, existing tech spec, package manifest/lockfile, explicit spec-gap context | Tech spec |
| **`mano ux`** | Defines UX flows — screens, navigation, user interactions. One screen at a time, only new or changed. | Phase brief, UX flow, tech spec, project rules | UX flow |
| **`mano rules`** | Defines and updates project rules — components, patterns, naming, a11y, folder structure. Flags over-engineering. Most useful once the tech stack is known. | Tech spec (recommended), UX flow, backlog, phase brief, existing project rules | Project rules |
| **`mano ui`** | Establishes the visual language — palette, typography, spacing, component guide. Generates a preview HTML. | Phase brief, UX flow, tech spec, project rules, backlog | Design brief, design preview |
| **`mano stories`** | Breaks the phase into implementable stories. Writes directly to files. Flags overloaded screens. | Phase brief, tech spec, UX flow, design brief, project rules | Story files, stories index |
| **`mano review`** | Collects feedback after shipping, triages into backlog, writes review log. | Stories index, phase brief, reviews, backlog | Review log, backlog updates |
| **`mano dev`** | Implements the next pending story for the active phase. Not a planning lens — follows the `AGENTS.md` implementation contract. | Stories index, the selected story, `AGENTS.md` contract | Source code, story marked `done` |

## Status

When the user types `mano status`:
1. Scan `_mano_output/`. If it doesn't exist, tell the user no project is in progress and suggest `mano start`.
2. Report: active phase, what files exist, what is missing, and what is present-but-incomplete.
3. If multiple planning actions are still reasonable, show them as `Next options` instead of forcing a single `Suggested next action`.
4. Only show one `Suggested next action` when the next move is genuinely narrower than the other valid options.
5. For user-facing or mobile phases, missing `design-brief.md` and `design-preview.html` should keep `mano ui` visible as a valid next option unless the current phase is already obviously ready for stories without further design clarification.
6. Do not activate any skill.

## Single obvious next action gates

`mano continue` should auto-run only when the next planning action is genuinely narrower than the alternatives.

Auto-run is appropriate when:
- no `_mano_output/` exists → `mano start`
- a phase brief exists and supporting artifacts are either already present, irrelevant, or explicitly skipped → `mano stories`
- all stories are done and no review entry exists → `mano review`
- the latest phase is reviewed and the user asks to keep going → `mano start`

Do not auto-run when:
- spec, UX, rules, or UI are all still plausible options for adding useful clarity
- the phase is user-facing and design context may materially change stories
- the tech approach is unclear enough that stories would become guesswork
- an artifact is stale or conflicting and the right repair path is not obvious
- the project is in build mode with pending stories

In those cases, show `Next options` instead of choosing for the user.

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
- Use `mano dev` to implement the next pending story.
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

  start    — Scope a new project or phase (`mano start`)
→ spec     — Tech spec (`mano spec`)
  ux       — UX flow (`mano ux`)
  rules    — Project rules (`mano rules`)
  ui       — Design brief and component guide (`mano ui`)
  stories  — Break phase into implementable stories (`mano stories`)
  review   — Triage feedback, close the phase (`mano review`)
  dev      — Implement the next pending story

→ marks the suggested next action.
Type: mano start, mano [action], or mano dev
```

When the phase is in build mode (stories exist and some are `pending`), mark `dev` as the suggested next action.

When the user types `mano [action]`:
- Execute the specific action logic defined in the `skills/` file.
- Default to **One-Shot** generation for write flows unless the skill file explicitly defines a multi-turn conversation.
- `mano review` is not one-shot during feedback capture and triage; follow `mano review`'s multi-turn contract exactly.
- `mano ui` must begin with one brief preference-capture step on first-run design generation when visual preferences are not already defined; after that reply, `mano ui` generates files in one shot.
- Output a single execution log snippet to the user, not conversational dialogue.

Valid actions: `spec` (`mano spec` — `tech-spec.md`), `ux` (`mano ux` — `ux-flow.md`), `rules` (`mano rules` — `project-rules.md`), `ui` (`mano ui` — `design-brief.md` + `design-preview.html`), `stories` (`mano stories` — `phase-[N]/stories/`), `review` (`mano review` — `reviews.md`).

## First run — new project

Human approval boundary: `mano start` may create or update the backlog and suggest a phase, but it must not write `phase-[N]/phase-brief.md` or mark items as `in-phase-[N]` until the user explicitly approves the phase scope.

```
User types: mano start

Step 1 — `mano start` activates
  Creates _mano_output/ if it doesn't exist.
  Copies AGENTS.md to the project root if it doesn't exist.
  Does not create optional artifacts such as project-rules.md.
  Presents numbered intake prompt or reads the provided PRD/brief.

Step 2 — Understand the why
  `mano start` asks about the pain point and existing solutions.
  Skip if already explained.

Step 3 — Clarification
  Focused questions. Skip if input is clear.

Step 4 — Design principle
  One tradeoff question. One sentence output.

Step 5 — Populate the backlog
  Decompose everything into backlog items.
  Write to _mano_output/backlog.md with all items as Status: backlog.

Step 6 — Suggest phase scope
  Suggest items from the backlog.
  One testable layer per phase.
  Stop and wait for explicit human approval or adjustment.

Step 7 — Validate, clarify, draft brief
  Show selected items with context.
  Surface review insights if returning.
  Clarify problem/scope issues (not tech decisions).
  Draft phase brief. User confirms.

Step 8 — Finalise
  Runs only after explicit human approval of the phase scope.
  Creates _mano_output/phase-[N]/.
  Writes phase-brief.md.
  Updates approved backlog items to in-phase-[N].
  Writes deferred items to backlog.
  Suggests next actions:
    any order: spec, ux, rules, ui, stories
```

## Phase review and triage

```
User types: mano review

Step 1 — Pre-review gate
  `mano review` checks stories README index.
  If stories are pending, asks user to mark done, cut, or come back later.

Step 2 — Feedback capture
  If the activation message already includes review feedback, `mano review` uses it directly once the pre-review gate is clear.
  Otherwise `mano review` shows the phase goal from the brief and asks the user to write freely about what's good, broken, annoying, new ideas.

Step 3 — Triage
  `mano review` categorises feedback into five buckets:
  🐛 Defects — broken things from this phase
  🔧 Refinements — things that work but could be better
  ✨ New ideas — emerged from usage, not originally scoped
  📋 Spec gaps — missing or unclear tech spec (if applicable)
  📏 Rule gaps — missing or unclear rules (if applicable)

  Defect descriptions stay as review input only.
  `mano review` does not debug, diagnose, or fix anything during `mano review`.

  Presents categorised list.
  User can reclassify items between buckets.

Step 4 — Close
  User confirms triage.
  `mano review` writes ALL items to backlog with categories preserved.
  `mano review` writes review summary to reviews.md.
  Phase is closed.
  `mano review` suggests: mano start for next phase, or stop.
```

## Minimal pipeline

When the phase is already clear and extra artifacts would add overhead instead of clarity:
- Skip `spec`, `ux`, `rules`, and `ui`.
- Use `mano start` → `mano stories` → build → `mano review`.
- Add optional planning artifacts later only if the work becomes ambiguous.

`mano review` is the one non-optional step. It is what closes a phase: only `mano review` moves the phase's backlog items off `in-phase-[N]` to `resolved`, and `mano start`'s `mano start` gate requires that closure before it will scope the next phase. The optional planning actions (`spec`, `ux`, `rules`, `ui`) can be skipped; review cannot.

## Rules

- The user owns scope, priorities, and product tradeoffs. `mano spec` may recommend technical defaults, `mano ui` may set visual defaults, and `mano rules` may recommend project rules, but every recommendation is overridable.
- Keep phase briefs concise enough to read in under two minutes. Target roughly 250-500 words plus short lists.
- Actions are a la carte, but some require upstream context or will redirect instead of guessing.
- Each phase brief is self-contained. No external files needed to understand it.
- The filesystem is the state. No progress file. Mano scans `_mano_output/` to know where you are.
- Skills read only what they need (see skill files for specific inputs).


## Human Oversight

Mano assumes humans actively supervise planning outputs.

LLMs may:
- make unsupported assumptions
- merge conflicting context
- preserve outdated decisions
- generate overconfident recommendations

Humans are responsible for:
- validating important decisions
- resolving ambiguity
- rejecting unnecessary complexity
- deciding when artifacts should be regenerated

Mano structures collaboration. It does not replace judgment.

## Compactness Guidelines

Artifacts should prioritize clarity over completeness.

Prefer:
- short sections
- tables over prose
- concrete decisions over speculation
- current-phase needs over future-proofing

Avoid:
- speculative scalability planning
- unused abstractions
- excessive rationale
- documenting hypothetical futures

## Chat Output After Writing Artifacts

When a skill creates or edits a file, the artifact is the deliverable — not a chat narrative about it. The human reviews the file (or its diff), not a prose retelling.

After writing or updating any artifact, output a terse changelog, not a summary:

- One header line naming the file touched.
- A compact bullet per change: section or area + what changed, in a few words. No rationale prose, no re-explaining content that is now in the file.
- Findings, risks, or constraint violations get an explicit `⚠ Flag:` line. These are the one thing that must stay visible in chat because they are not obvious from reading the artifact.
- If something could not be done or an assumption was made, say so. Otherwise stop — do not pad.

Do not produce "✅ Done — here is everything I wrote" recaps that restate the artifact's contents. Restating a file the human is about to open adds no information and only grows the conversation. This applies to every skill, including third-party and external skills.

### Canonical execution-log format

Every skill's completion log uses exactly this shape. Do not add `Scope:` or `Action:` lines — the active phase and the touched file are already obvious from context and git history; restating them is the noise users have explicitly rejected.

```text
[Name]: mano <command> — <file(s) touched>
- <substantive decision or change, a few words>
- <substantive decision or change, a few words>
⚠ Verify: <assumption or material change the user should sanity-check before relying on it>

Next:
- `mano <x>` — <when it applies>
```

Rules:
- Header is one line: who, which command, which file(s). Nothing else.
- Bullets carry only substantive content (key decisions, screens/categories changed, stories inserted, palette). Never process narration.
- `⚠ Verify:` appears only when the artifact embeds an assumption, a hardcoded placeholder, or a material change the user did not explicitly ask for (e.g. a backported decision). Omit the line entirely when there is nothing to flag. This applies to every skill, not just spec — if an artifact contains a `Note`/assumption worth checking, surface it here.
- `Next:` keeps the existing next-action options; it is not boilerplate and stays.

Reason fully; externalize sparingly. Terse output is a rule about *display*, not *cognition*. Judgment-heavy skills (scoping, story decomposition, spec, rules, review) must still do the deliberation their contract requires — specificity, branching-flow, exhaustiveness, anti-rationalization gates. Do not shortcut that thinking to save chat volume; under-reasoning a planning decision is far more expensive than over-explaining one, because the bad decision propagates into every downstream artifact. The discipline is: do the reasoning internally, let the artifact carry the conclusions (each artifact is self-contained by design), and put only the changelog, flags, and genuine unresolved questions in chat. Do not narrate the deliberation itself. Mechanical steps (status updates, file writes, hook checks) carry no judgment worth narrating — just act and report.

## Artifact Quality

Planning artifacts are written for human readers — people who will read, discuss, edit, and act on them. They are not structured inputs for AI models.

Write naturally. Use short paragraphs where prose works better than bullet lists. Concrete and specific beats abstract and hedged. A phase brief should read like a note to a colleague. A backlog item should read like something you'd write yourself. A project rule should read like a convention a team member can apply without a meeting.

**The one exception:** the `Implementation Reference` section in story files is deliberately written for coding agents. Everything else in every artifact is for humans.

If a section reads like structured machine-parseable metadata rather than human communication, it is too heavy. Trim it, merge it with adjacent content, or leave it out.

## Shared Values: One Canonical Home

A shared fact — a measurement, constant, threshold, contract value, token, or any number a future contributor must apply consistently — has exactly **one owning artifact** that states its value, its unit, and the rationale for it. The owner is the artifact closest to the decision: usually `tech-spec.md` for a technical constraint, `design-brief.md` for a purely visual token. When the value is enforced at runtime, it is mirrored by exactly one named code constant (e.g. `TOUCH_TARGET_MIN_PX`), and the code constant is the runtime source of truth.

Every other artifact **references the owner by name** ("touch targets meet the minimum defined in `tech-spec.md`") instead of restating the number. The number lives once, in the one place a reader would look for it.

Stating the same value in a second artifact is drift, not redundancy — and stating it in a *different unit* (e.g. `44pt` in one file, `88px` in another, `36px` in a third) is the most dangerous form, because it hides agreement and disagreement equally: a reader cannot tell whether `44pt` and `88px` are the same fact or a conflict. When you find a value expressed in mixed units across artifacts, converge them on the owner's single unit, or convert and cite ("44pt = 88px at 2× DPI") only in the owning artifact.

This applies to **every** artifact edit, whether made inside a skill or as a direct request. Propagating one value into several files and reporting that as completed alignment is the failure this rule exists to prevent — alignment means converging on the reference, never replicating the literal.

## Conflicting Values: Surface, Do Not Reconcile

Before writing a value that already appears in another artifact, check whether the existing copies agree — comparing the *fact*, not the *string* (`44pt` and `88px at 2×` agree; `44pt` and `36px` do not).

If they differ in number or in unit, **stop and surface the conflict for a human decision** before writing anything. State what each artifact currently holds and which one the human's instruction would change. Never silently converge the values, never silently pick the number from the latest instruction, and never report a reconciliation as completed work. A pre-existing cross-artifact disagreement is a decision the human owns — it may encode an intentional difference, a forgotten backport, or a real bug — and the agent's job is to make it visible, not to flatten it. Reporting "updated all N files to the same value" over a conflict the human never resolved is the exact failure this rule prevents.

## Backlog Ownership Boundary

`mano start` and `mano review` own backlog content and long-lived project continuity.

Other skills should not edit the backlog except for narrow gap-resolution status updates:
- `mano spec` may mark an explicitly provided `spec-gap` as resolved after updating the technical specification.
- `mano rules` may mark an explicitly provided `rule-gap` as resolved after updating project rules.

Skills should not inspect the backlog for general project memory unless their role explicitly owns that context.

## Skill Tightening

Use these patterns inside skills when outputs start becoming vague, overconfident, or too broad.

### Anti-Rationalization

Do not allow a skill to excuse weak work.

If the available context is insufficient, the skill should:
1. state what is missing
2. explain the risk or tradeoff
3. produce a smaller useful output if possible
4. avoid inventing certainty

### Exit Criteria

Before finalizing an artifact, check that it is:
- scoped to the current phase
- human-readable and directly editable
- free of unnecessary process or speculative future work
- explicit about assumptions and unresolved questions
- useful for the next action

### Progressive Disclosure

Default to the smallest relevant context.

Only request or load additional artifacts when they materially change the current output.

## Optional Post-Skill Hooks

Mano supports optional post-skill hooks in `_mano/hooks/`.

Hooks are suggest-only. They never run automatically.

After any Mano skill completes, check for an active hook matching the skill name:

```text
_mano/hooks/post-[skill].md
```

Ignore example hooks:

```text
_mano/hooks/post-[skill].example.md
```

Examples:
- `mano start` checks for `_mano/hooks/post-start.md`
- `mano spec` checks for `_mano/hooks/post-spec.md`
- `mano rules` checks for `_mano/hooks/post-rules.md`
- `mano ux` checks for `_mano/hooks/post-ux.md`
- `mano ui` checks for `_mano/hooks/post-ui.md`
- `mano stories` checks for `_mano/hooks/post-stories.md`
- `mano review` checks for `_mano/hooks/post-review.md`

If an active hook exists, mention it in the final chat response before the next-action block and ask whether to run it.

Use this format:

```text
Active post-[skill] hook found: `_mano/hooks/post-[skill].md`.
-> Purpose: Optional specialist review of the generated or current artifact.
-> Recommended timing: Run after reviewing the artifact and before the next dependent Mano action if this check matters for the phase.
```

Do not run the hook without explicit user confirmation.

Do not print the hook's suggested prompt unless the user asks to run or view the hook.

Do not mention specific third-party or external skill names in generic Mano output.

Do not write hook suggestions into generated artifacts.

Hooks are best run after the human has reviewed or accepted the generated artifact. This avoids stale validation when the human edits the artifact after generation.

Hooks are for optional review, validation, or project-specific checks. They are not mandatory hidden workflow steps.