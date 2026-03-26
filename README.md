# Mano

A structured thinking tool for AI-assisted software planning. Phased, feedback-driven, anti-slop.

Mano helps you scope, challenge, and spec one shippable phase at a time. It uses persona constraints to surface issues you'd miss working linearly. It is not a multi-agent system — it is one model applying different lenses to your idea.

## Commands

| Command | What it does |
|---------|-------------|
| `mano` | Show available commands and current status. |
| `mano status` | Scans output folder. Where am I? What's next? |
| `mano start` | Scope a new project or phase. (Skye, optionally Alex) |
| `mano [action]` | Run an action: `spec`, `ui`, `stories`, `review`. Any order, any time. |
| `mano continue` | Auto-run the next logical action. |
| `mano help [persona]` | Show what a persona does and when to use it. |

Actions are independent, not sequential. Run them in any order. Each persona checks for its inputs and warns you if something is missing — but won't refuse to run.

`mano [action]` handles everything — first run, discussion, and regeneration. Run it again on the same action to discuss changes or regenerate output.

## Personas

| Name | Role | File |
|------|------|------|
| **Skye** | Scopes the idea, challenges the why, proposes phases | `personas/start.md` |
| **Dave** | Phase review, triage, escape velocity | `personas/review.md` |
| **Alex** | Stress-tests assumptions and flags risks (triggered by Skye) | `personas/challenger.md` |
| **Helen** | Translates the phase brief into tech spec and UX flow | `personas/spec.md` |
| **Luna** | Establishes visual language and component guide | `personas/ui.md` |
| **Marco** | Breaks specs into implementable stories | `personas/stories.md` |

These are structured constraint lenses, not simulated experts. They surface issues through mechanical rules (asymmetric information, forced scoring, mandatory rejection), not through genuine independent thought.

## How it works

### Full pipeline (complex projects)
1. `mano start` → Skye scopes. Optionally Alex challenges.
2. `mano spec` → Helen writes tech spec + UX flow.
3. `mano ui` → Luna creates design brief + preview (once per project).
4. `mano stories` → Marco breaks into stories.
5. Build. Ship. Gather feedback.
6. `mano review` → Dave triages feedback into defects, refinements, and new ideas. Fix what matters, defer the rest, then scope the next phase.

### Light pipeline (simple projects or later phases with momentum)
1. `mano start` → Skye scopes. Skip challenge.
2. `mano stories` → Marco writes stories directly.
3. Build.

### Escape hatch
After fixes are resolved in a review, Dave offers light mode, full pipeline, or "I'm good." A tool that never lets go is a dependency, not a tool.

### Mid-build feedback
Requirements change during implementation. You don't have to finish the phase to adjust:

- **Found a bug or missing feature?** Use `mano stories` — Marco will create a new story (numbered 3a, 3b, etc.) and ask whether to implement it now or queue it for later.
- **Need to change scope?** Use `mano start` to talk to Skye — update assumptions, adjust scope, flag stories that turned out wrong.
- **Need to regenerate specs or stories?** Run `mano [action]` again — the persona will check what exists and offer to update or regenerate.

The pipeline doesn't require you to finish before course-correcting.

### Best practice: fresh chat per action

Every Mano file lives on disk — phase brief, tech spec, stories, design brief. A new chat reads the same files and picks up where you left off. You don't need conversation history.

Start a fresh chat for each `mano` command — especially `mano review` and `mano stories`. Long sessions accumulate context that confuses personas: "review" triggers code review instead of Mano's triage, Marco tries to fix bugs instead of writing stories. A clean context means the persona file is the only instruction the model sees.

## Output

```
_mano_output/
├── backlog.md               ← future work, deferred items, ideas (Skye + you)
├── tech-spec.md             ← project-wide, cumulative (Helen extends per phase)
├── ux-flow.md               ← project-wide, cumulative (Helen extends per phase)
├── design-brief.md          ← project-wide visual language (if generated)
├── design-preview.html      ← visual preview (if generated)
├── project-rules.md         ← component patterns, architecture, a11y (if generated)
├── reviews.md               ← sprint review log, human-only, no persona reads this
├── phase-1/
│   ├── phase-brief.md       ← problem, vision, scope for this phase
│   └── stories/
│       ├── README.md         ← story index
│       └── story-*.md        ← one file per story
├── phase-2/
│   └── ...
└── ...
```

Each phase brief is self-contained — problem, vision, design principle, scope. Technical decisions and UX flow live at project level and grow across phases. Future work lives in `backlog.md`.

## Customisation

### Design constraints
Create `_mano/design-constraints.md`. Luna and Marco will respect it. A starter template is at `_mano/templates/design-constraints.md`.

### Project rules
Created by Marco during `mano stories` if you choose to set them, or add your own anytime. Covers component patterns, architecture decisions, accessibility, naming — anything the coding agent must follow. Lives at `_mano_output/project-rules.md`.

### Persona overrides
Create `_mano/custom/[persona].md` to override any default persona.
