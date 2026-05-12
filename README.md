# Mano

Mano is a lightweight context-discipline protocol for adaptive AI-assisted software planning.

It helps developers use AI as a thinking partner while keeping humans in charge of scope, architecture, product tradeoffs, and implementation decisions.

Mano is built around a simple assumption: software projects rarely move in a straight line. User feedback, testing, technical discovery, and changing priorities invalidate early assumptions. The goal is not to generate a perfect upfront plan. The goal is to keep planning cheap to revise as understanding changes.

Mano does this by breaking work into small shippable phases, using only the context needed for the current phase, and keeping artifacts explicit, lightweight, and disposable when they stop being useful.

> **Important:** Mano is not a compiled CLI tool, a deterministic software framework, or an autonomous planning system. It is a set of personas, skills, templates, and instructions that rely entirely on your AI agent's context window. You, the human, are the ultimate enforcer of scope, context, and quality.

## Core Principles

### Human judgment stays in control

Mano supports engineering judgment; it does not replace it. The AI may challenge vague ideas, surface gaps, suggest defaults, and help decompose work, but the human owns the final decisions.

### Adaptive planning beats predictive planning

Mano expects plans to change. Artifacts should evolve when real feedback, implementation constraints, or better understanding invalidate earlier assumptions. Change is a normal part of the workflow, not a failure of planning.

### Low-cost adaptation

Mano optimizes for reducing the cost of changing direction. Small phases, short tickets, focused context, and lightweight artifacts make it easier to update the plan without rewriting a large pre-planned system.

### Planning compression

Mano deliberately keeps planning surface area small. Use the minimum artifacts needed to make the next phase clear enough to build. Do not generate specs, UX docs, rules, or UI guidance just because they exist as actions.

### AI as a thinking partner

Mano should help you think more clearly, not encourage passive acceptance. Skills are expected to challenge abstraction, short-sighted decisions, missing assumptions, and overloaded scope.

## Commands

| Command | What it does |
|---------|-------------|
| `mano` | Show available commands and current status. |
| `mano status` | Scans output folder. Where am I? What's next? |
| `mano start` | Scope a new project or phase. This is a dedicated command, not part of `mano [action]`. (Skye) |
| `mano [action]` | Run a planning action: `spec`, `ux`, `rules`, `ui`, `stories`, `review`. Any order, when its inputs are useful. |
| `mano continue` | Auto-run only when there is a single obvious next planning step. If several planning actions are still reasonable, it stops and shows the options instead of picking the shortest path. |
| `mano help [skill]` | Show what a skill does and when to use it. |

Actions are independent, not sequential. There is no fixed conveyor belt, but not every action is equally useful at every moment. Each skill checks for required context first: some can proceed with partial inputs, others warn and redirect you to the action that creates the missing artifact.

When a user types a Mano command in their AI IDE's chat interface, the agent is instructed to carry out that planning command directly. Since this relies entirely on the agent's context window and instruction-following capabilities, you must actively steer the agent if it hallucinates state or breaks character.

`mano [action]` handles everything — first run, discussion, and regeneration. Run it again on the same action to discuss changes or regenerate output.

## Skills

| Name | Role | File |
|------|------|------|
| **Skye** | Scopes the idea, populates the backlog, proposes phases | `skills/start.md` |
| **Alex** | Defines and updates project rules — components, patterns, architecture | `skills/rules.md` |
| **Helen** | Translates the phase brief into tech spec | `skills/spec.md` |
| **Rob** | Defines UX flows — screens, navigation, user interactions | `skills/ux.md` |
| **Luna** | Establishes visual language and component guide | `skills/ui.md` |
| **Marco** | Breaks specs into implementable stories | `skills/stories.md` |
| **Dave** | Phase review, triage, closes the phase | `skills/review.md` |

These are structured constraint lenses, not simulated experts. They surface issues through mechanical rules and focused responsibilities, not through genuine independent thought.

The user owns scope, priorities, and product tradeoffs. Helen can recommend concrete technical defaults and Luna can set a concrete visual direction, but both are always overridable.

## How it works: The "À La Carte" Philosophy

Mano is strictly **à la carte** and functions as a **Just-In-Time (JIT) planning** system.

You only pay the cognitive tax for what you are building *today*. Only two actions are usually required to execute a phase: `mano start` to scope the work, and `mano stories` to generate the tasks. Every other action (`spec`, `ux`, `rules`, `ui`) is optional context tightening.

Optional actions can be created now, reused from existing work, copied from a similar project, adapted from external inputs, or skipped entirely when they would add noise. Only run them when the current phase needs more clarity, constraints, or alignment. You never run the whole pipeline "just in case."

### Example fuller pass
1. `mano start` → Skye scopes and populates the backlog.
2. `mano spec` → Helen writes tech spec.
3. `mano ux` → Rob defines UX flow (for user-facing phases).
4. `mano rules` → Alex defines project rules (recommended for new projects).
5. `mano ui` → Luna creates or updates design brief + preview.
6. `mano stories` → Marco breaks into stories.
7. Build. Ship. Gather feedback.
8. `mano review` → Dave triages feedback into the backlog, writes the review log, closes the phase.

This is an example path, not a mandatory conveyor belt. After any step, choose the next action from the artifacts that are still missing or need revision.

### Minimal phase
1. `mano start` → Skye scopes.
2. `mano stories` → Marco writes stories directly.
3. Build.

Use the minimal path when the phase is already clear and extra artifacts would add noise instead of signal.

### Escape hatch
After a review, Dave closes the phase. If you don't need Mano for the rest — that's fine. A tool that never lets go is a dependency, not a tool.

### Mid-build feedback
Requirements change during implementation. You don't have to finish the phase to adjust:

- **Found a bug or missing feature?** Use `mano stories` — Marco will create a new story (numbered 3a, 3b, etc.) and ask whether to implement it now or queue it for later.
- **Need to change scope?** Use `mano start` to talk to Skye — update assumptions, adjust scope, flag stories that turned out wrong.
- **Need to regenerate specs or stories?** Run `mano [action]` again — the skill will check what exists and offer to update or regenerate.

For `mano spec`, rerunning the command is also how you sync the planning doc back to reality after project setup. Once the project has a real `package.json` and lockfile, or anytime you add/remove/replace a library, run `mano spec` again so Helen can reconcile `_mano_output/tech-spec.md` with the actual installed toolchain.

The pipeline doesn't require you to finish before course-correcting.

## Output

```
_mano_output/
├── backlog.md               ← future work, deferred items, review follow-ups (owned by Skye, updated by Dave, editable by you)
├── tech-spec.md             ← project-wide, cumulative (Helen extends per phase)
├── ux-flow.md               ← project-wide, cumulative (Rob extends per phase)
├── design-brief.md          ← project-wide visual language (if generated)
├── design-preview.html      ← visual preview (if generated)
├── project-rules.md         ← seeded from template; Alex owns substantive rules, Luna may seed accessibility level if blank
├── reviews.md               ← review log; Skye reads this when shaping later phases
├── phase-1/
│   ├── phase-brief.md       ← problem, vision, scope for this phase
│   └── stories/
│       ├── README.md         ← story index
│       └── story-*.md        ← one file per story
├── phase-2/
│   └── ...
└── ...
```

Each phase brief is self-contained — problem, vision, design principle, scope, assumptions, and risks. Technical decisions and UX flow live at project level and grow only when they are useful. Future work lives in `backlog.md`. Artifacts are living working documents, not permanent contracts.

Planning artifacts live under `_mano_output/`. The only framework scaffold written outside that folder is `AGENTS.md` at the project root, copied during `mano start` so coding agents know where Mano artifacts live.

Mano's installed runtime layout lives under `_mano/` inside the user's project. This repository contains the framework source files at the root for authoring, but the contract exposed to coding agents in real projects uses `_mano/skills`, `_mano/templates`, and `_mano/custom`.

### A Warning on State Detection

Mano tells the AI to treat the filesystem as the source of truth, "scanning" `_mano_output/` to determine the current project state. **However, AI agents do not natively scan files unless those files are injected into their context window.** If the agent confidently hallucinates a wrong state, it is because it lacks context. You must explicitly @-mention the relevant `_mano_output/` files to ground it back in reality.

## Customisation

You can override or guide the framework's default behavior by adding specific files to your workspace.

### 1. Project Rules (`_mano_output/project-rules.md`)
This is the core configuration file that manages your architectural patterns, routing formats, and workflow preferences.
- **Creation:** Seeded automatically from a template when you run `mano start` (or if you skip straight to `mano stories`).
- **Updates:** `mano rules` is the primary command for updating this file. Other actions (like `mano ui` for accessibility settings) will append to it, but they will never overwrite your existing rules.

> **Spec vs Rules:** What's the difference? 
> Mano enforces a strict separation of concerns to prevent AI context bloat:
> - **`tech-spec.md` is the WHAT (The Blueprint):** It defines libraries, database schemas, and API contracts (e.g., "We will use PostgreSQL, and the `/users` endpoint returns JSON").
> - **`project-rules.md` is the HOW (The Building Codes):** It defines architectural patterns, folder structures, and styling guidelines (e.g., "All API handlers must be wrapped in `catchAsync`, and we separate UI logic from data fetching").

### 2. Story Template Override (`_mano/custom/story.md`)
Use this when you want Marco to keep the same planning behavior but emit stories in a different shape.
- Copy one of the shipped examples to `_mano/custom/story.md` and edit it.
- Available examples:
	- `_mano/custom/story.example.md` — default human-friendly format
	- `_mano/custom/story.example.as-i-so.md` — classic `As a / I want / So that` format
	- `_mano/custom/story.example.given-when-then.md` — scenario-led `Given / When / Then / And` format
- Choose this when you want a different story document structure, not when you want to change Marco's decision-making. The implementation contract still stays mandatory: custom templates should preserve a clear acceptance section, scope boundary, `Implementation Reference`, and completion footer.

### 3. Skill Overrides (`_mano/custom/[skill].md`)
If you want to fundamentally change how a skill plans or generates output, you can completely override their default instructions. 
- Create a Markdown file matching the skill's name (e.g., `_mano/custom/ui.md`) containing your custom prompt.

### 4. Bring Your Own Artifacts
Because Mano operates on a strictly "à la carte" file-based system, you can completely skip a skill by providing your own documentation. If you already have a spec or design, simply create the corresponding file in `_mano_output/` and Mano will read and respect it automatically:
- `design-brief.md`
- `tech-spec.md`
- `ux-flow.md`
- `project-rules.md`


# Reality of Context

Mano does not create true agent isolation, persistent memory, or deterministic workflows.

LLMs only reason over the context currently provided to them. Artifact boundaries, role specialization, and phase separation are maintained through user discipline and selective context exposure — not hard enforcement.

Mano reduces planning entropy by encouraging bounded reasoning scopes and structured project artifacts, but humans remain responsible for:
- validating outputs
- resolving contradictions
- detecting stale assumptions
- deciding what context to expose

This is not a fully autonomous system. It is a collaboration framework for guiding LLM-assisted planning work.

# Artifact Trust Hierarchy

When artifacts conflict, prefer sources in this order:

1. Explicit human decisions
2. Current phase brief
3. Project rules
4. Technical specifications
5. UX/UI documentation
6. Generated stories or tasks

Lower-level artifacts should be regenerated or updated when they drift from higher-priority decisions.

# Artifact Drift

Project artifacts may become outdated as decisions evolve.

Artifacts can exist in four states:
- Current — aligned with latest project direction
- Stale — partially outdated but still useful
- Conflicting — contradicts newer decisions
- Deprecated — retained only for historical reference

When major decisions change, regenerate downstream artifacts rather than patching inconsistencies incrementally.

# Common Failure Modes

Mano cannot eliminate typical LLM failure patterns.

Watch for:
- stale artifact assumptions
- contradictory project documents
- speculative architecture growth
- overconfident recommendations
- context leakage between planning phases
- unnecessary process expansion

When outputs become unfocused or contradictory, reduce context scope and regenerate artifacts from the latest trusted decisions.


## Human-Readable Artifacts

Mano artifacts are optimized for humans first. They should be easy to read, edit, trim, or replace manually without rerunning a skill. Skills accelerate planning, but they do not own the documents.

The backlog may include a short optional `Core Product Principles` section for durable product intent that should survive across phases, such as speed, simplicity, interaction feel, accessibility posture, or other values that would be easy to lose during iterative planning. Keep it small and human-editable.

## Core Principles and Phase Context

The backlog may contain a short, optional `Core Product Principles` section for durable product values that should survive across phases.

This can include expectations such as speed, simplicity, interaction feel, accessibility level, tone, or other product values that are easy to lose during iterative planning.

These principles do not need a separate process or artifact. They are human-readable backlog content.

Skye owns this continuity and should copy only the principles relevant to the current phase into the phase brief. Downstream skills should operate from the phase brief and explicitly provided context rather than reading the backlog for general project memory.

## Skill Tightening Patterns

Mano can use small skill-tightening patterns without changing its philosophy.

These patterns are not extra process steps. They are lightweight guardrails that make skills more predictable, especially with smaller models.

### Anti-Rationalization

Skills should not justify weak outputs with excuses such as:
- "This is enough for now" when important ambiguity remains.
- "The user can figure it out later" when a decision affects the current phase.
- "This is obvious" when the artifact does not state the reasoning clearly.
- "We can add detail later" when missing detail blocks implementation.
- "The model probably knows" when context was not provided.

When a skill cannot produce a useful artifact from the available context, it should say what is missing, explain the tradeoff, and offer a smaller useful next step.

### Exit Criteria

Artifacts should have simple "good enough" checks.

Exit criteria are not approval gates. They help humans quickly judge whether an artifact is usable, incomplete, or too vague.

A Mano artifact is usually good enough when:
- it supports the current phase
- it is readable and editable by a human
- it avoids unnecessary future planning
- it exposes important assumptions
- it gives the next skill or developer enough context to continue

### Progressive Disclosure

Skills should load or request only the context needed for the current task.

Prefer:
- phase brief before full backlog
- relevant artifact sections before entire documents
- explicit provided context before inferred project memory
- small targeted follow-up questions before broad discovery

Avoid pulling every artifact into every skill. Mano should preserve useful reasoning quality by keeping context bounded.

## Optional Post-Skill Hooks

Mano can support optional post-skill hooks through a local `hooks/` folder.

Hooks are not part of the default workflow. They are a project-level extension point for users who want to run extra checks or external skills after a Mano skill creates or updates artifacts.

This keeps Mano's core workflow small while allowing local experimentation.

Post hooks should be:
- optional
- explicit
- post-skill only
- scoped to files touched by the original skill
- advisory by default

Example inactive hook files use the `.example.md` suffix:

```text
hooks/post-spec.example.md
hooks/post-stories.example.md
hooks/post-review.example.md
```

To test a hook, copy or rename it to the active post-hook name, for example `hooks/post-spec.md`.

Hooks should not define the main workflow, automatically load broad context, or become mandatory gates unless the project deliberately chooses that convention.
