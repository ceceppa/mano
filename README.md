# Mano

A structured thinking tool for AI-assisted software planning. Phased, feedback-driven, anti-slop.

Mano helps you scope, spec, and build one shippable phase at a time. It uses persona constraints to surface issues you'd miss working linearly. It is not a multi-agent system — it is one model applying different lenses to your idea.

## Commands

| Command | What it does |
|---------|-------------|
| `mano` | Show available commands and current status. |
| `mano status` | Scans output folder. Where am I? What's next? |
| `mano start` | Scope a new project or phase. (Skye) |
| `mano rules` | Define or update project rules. (Alex) |
| `mano [action]` | Run an action: `spec`, `ux`, `ui`, `stories`, `review`. Any order, when its inputs are useful. |
| `mano continue` | Auto-run the next logical action. |
| `mano help [persona]` | Show what a persona does and when to use it. |

Actions are independent, not sequential. There is no fixed conveyor belt, but not every action is equally useful at every moment. Each persona checks for required context first: some can proceed with partial inputs, others warn and redirect you to the action that creates the missing artifact.

`mano [action]` handles everything — first run, discussion, and regeneration. Run it again on the same action to discuss changes or regenerate output.

## Personas

| Name | Role | File |
|------|------|------|
| **Skye** | Scopes the idea, populates the backlog, proposes phases | `personas/start.md` |
| **Alex** | Defines and updates project rules — components, patterns, architecture | `personas/rules.md` |
| **Helen** | Translates the phase brief into tech spec | `personas/spec.md` |
| **Rob** | Defines UX flows — screens, navigation, user interactions | `personas/ux.md` |
| **Luna** | Establishes visual language and component guide | `personas/ui.md` |
| **Marco** | Breaks specs into implementable stories | `personas/stories.md` |
| **Dave** | Phase review, triage, closes the phase | `personas/review.md` |

These are structured constraint lenses, not simulated experts. They surface issues through mechanical rules and focused responsibilities, not through genuine independent thought.

The user owns scope, priorities, and product tradeoffs. Helen can recommend concrete technical defaults and Luna can set a concrete visual direction, but both are always overridable.

## How it works

### Full pipeline (complex projects)
1. `mano start` → Skye scopes and populates the backlog.
2. `mano spec` → Helen writes tech spec.
3. `mano ux` → Rob defines UX flow (for user-facing phases).
4. `mano rules` → Alex defines project rules (recommended for new projects).
5. `mano ui` → Luna creates or updates design brief + preview.
6. `mano stories` → Marco breaks into stories.
7. Build. Ship. Gather feedback.
8. `mano review` → Dave triages feedback into the backlog, writes the review log, closes the phase.

### Light pipeline (simple projects or later phases with momentum)
1. `mano start` → Skye scopes.
2. `mano stories` → Marco writes stories directly.
3. Build.

### Escape hatch
After a review, Dave closes the phase. If you don't need Mano for the rest — that's fine. A tool that never lets go is a dependency, not a tool.

### Mid-build feedback
Requirements change during implementation. You don't have to finish the phase to adjust:

- **Found a bug or missing feature?** Use `mano stories` — Marco will create a new story (numbered 3a, 3b, etc.) and ask whether to implement it now or queue it for later.
- **Need to change scope?** Use `mano start` to talk to Skye — update assumptions, adjust scope, flag stories that turned out wrong.
- **Need to regenerate specs or stories?** Run `mano [action]` again — the persona will check what exists and offer to update or regenerate.

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

## Customisation

### Design constraints
Create `_mano/design-constraints.md`. Luna and Marco will respect it. A starter template is at `_mano/templates/design-constraints.md`.

### Project rules
Seeded from `_mano/templates/project-rules.md` during `mano start` so the workflow rules exist from day one. Alex owns the substantive rules and updates them during `mano rules`. If Luna captures an accessibility level before Alex runs, she may seed only the `Accessibility level:` line when that field is still blank; Alex remains the authority for the persisted rules file. If you skip straight to `mano stories` and the file is missing, Marco can create it from the same template. It lives at `_mano_output/project-rules.md`.

### Persona overrides
Create `_mano/custom/[persona].md` to override any default persona.
