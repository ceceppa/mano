# Mano

A structured thinking tool for AI-assisted software planning. Phased, feedback-driven, anti-slop.

Mano helps you scope, challenge, and spec one shippable phase at a time. It uses persona constraints to surface issues you'd miss working linearly. It is not a multi-agent system — it is one model applying different lenses to your idea.

## Commands

| Command | What it does |
|---------|-------------|
| `mano` | Show available commands and current status. |
| `mano-status` | Scans output folder. Where am I? What's next? |
| `mano-start` | Scope a new project or phase. (Skye, optionally Alex) |
| `mano-do [action]` | Run an action: `spec`, `ui`, `stories`, `review`. Any order, any time. |
| `mano-continue` | Auto-run the next logical action. |
| `mano-ask [action]` | Chat with a persona about their output. |
| `mano-redo [action]` | Regenerate a persona's output from scratch. |

Actions are independent, not sequential. Run them in any order. Each persona checks for its inputs and warns you if something is missing — but won't refuse to run.

## Personas

| Name | Role | File |
|------|------|------|
| **Skye** | Scopes the idea, challenges the why, proposes phases | `personas/start.md` |
| **Alex** | Stress-tests assumptions and flags risks (triggered by Skye) | `personas/challenger.md` |
| **Helen** | Translates the phase brief into tech spec and UX flow | `personas/spec.md` |
| **Mia** | Establishes visual language and component guide | `personas/ui.md` |
| **Marco** | Breaks specs into implementable stories | `personas/stories.md` |

These are structured constraint lenses, not simulated experts. They surface issues through mechanical rules (asymmetric information, forced scoring, mandatory rejection), not through genuine independent thought.

## How it works

### Full pipeline (complex projects)
1. `mano-start` → Skye scopes. Optionally Alex challenges.
2. `mano-do spec` → Helen writes tech spec + UX flow.
3. `mano-do ui` → Mia creates design brief + preview (once per project).
4. `mano-do stories` → Marco breaks into stories.
5. Build. Ship. Gather feedback.
6. `mano-do review` → Skye triages feedback into defects, refinements, and new ideas. Fix what matters, defer the rest, then scope the next phase.

### Light pipeline (simple projects or later phases with momentum)
1. `mano-start` → Skye scopes. Skip challenge.
2. `mano-do stories` → Marco writes stories directly.
3. Build.

### Escape hatch
After fixes are resolved in a review, Skye offers light mode, full pipeline, or "I'm good." A tool that never lets go is a dependency, not a tool.

### Mid-build feedback
Requirements change during implementation. You don't have to finish the phase to adjust:

- **Found a bug or missing feature?** Use `mano-ask stories` — Marco will create a new story (numbered 3a, 3b, etc.) and ask whether to implement it now or queue it for later. The stories index updates automatically.
- **Need to change scope?** Use `mano-ask start` to talk to Skye — update assumptions, adjust scope, flag stories that turned out wrong.
- **Need to regenerate stories?** Use `mano-redo stories` after scope changes.

The pipeline doesn't require you to finish before course-correcting.

## Output

```
_mano_output/
├── design-brief.md          ← project-wide visual language (if generated)
├── design-preview.html      ← visual preview (if generated)
├── coding-style.md          ← coding preferences (if generated)
├── phase-1/
│   ├── phase-brief.md       ← self-contained: problem, vision, scope, tech stack
│   ├── tech-spec.md         ← if generated
│   ├── ux-flow.md           ← if generated
│   └── stories/
│       ├── README.md         ← story index
│       └── story-*.md        ← one file per story
├── phase-2/
│   └── ...
└── ...
```

Each phase brief is self-contained. It carries the problem, vision, design principle, tech stack, and phase scope. No external file needed. Phase 2 copies from phase 1 and adjusts.

## Customisation

### Design constraints
Create `_mano/design-constraints.md`. Mia and Marco will respect it. A starter template is at `_mano/templates/design-constraints.md`.

### Coding style
Created by Marco during `mano-do stories` if you choose to set preferences. Lives at `_mano_output/coding-style.md`.

### Persona overrides
Create `_mano/custom/[persona].md` to override any default persona.
