# Mano

AI-assisted phase planning that keeps the human in control.

Mano is for developers who want AI to help plan work without handing the model control of implementation or product decisions.

Without structure, AI planning tends to collapse into vague chat, bloated process, or hidden decisions. Mano is an **LLM Workflow Protocol** that breaks work into one shippable phase at a time, keeps planning artifacts explicit in the filesystem, and keeps AI focused on bounded planning tasks instead of open-ended decision making. 

> **Important:** Mano is not a compiled CLI tool or a deterministic software framework. It is a set of personas and instructions that rely entirely on your AI agent's context window. You, the human, are the ultimate enforcer of these boundaries.

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

Mano is strictly **à la carte** and functions as a **Just-In-Time (JIT) Architecture** prompt system.

You only pay the cognitive tax for what you are building *today*. Only two actions are mandatory to execute a phase: `mano start` to scope the work, and `mano stories` to generate the tasks. Every other action (`spec`, `ux`, `rules`, `ui`) is floating and optional. 

Only run the optional tools if the phase you are actively working on requires them, or if you hit a pain point that requires you to establish a new architectural pattern. You never run the whole pipeline "just in case."

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

Each phase brief is self-contained — problem, vision, design principle, scope, assumptions, and risks. Technical decisions and UX flow live at project level and grow across phases. Future work lives in `backlog.md`.

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
	- `_mano/custom/story.example.corporate.md` — classic `As a / I want / So that` format
	- `_mano/custom/story.example.given-when-then.md` — scenario-led `Given / When / Then / And` format
- Choose this when you want a different story document structure, not when you want to change Marco's decision-making.

### 3. Skill Overrides (`_mano/custom/[skill].md`)
If you want to fundamentally change how a skill plans or generates output, you can completely override their default instructions. 
- Create a Markdown file matching the skill's name (e.g., `_mano/custom/ui.md`) containing your custom prompt.

### 4. Bring Your Own Artifacts
Because Mano operates on a strictly "à la carte" file-based system, you can completely skip a skill by providing your own documentation. If you already have a spec or design, simply create the corresponding file in `_mano_output/` and Mano will read and respect it automatically:
- `design-brief.md`
- `tech-spec.md`
- `ux-flow.md`
- `project-rules.md`
