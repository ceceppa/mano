# Changelog

A history of Mano's releases — what each version changes and why.

## 1.1.0 — June 24, 2026

### Added
- **`mano import`** — a dedicated skill that turns an existing PRD or document into a backlog, then stops. Decomposition logic (the central-noun gate, resolution test, pre-send filter) moved out of `mano start`'s PRD path into its own command. Run `mano import <doc>`, review the backlog, then `mano start` to scope the first phase.
- **Eval harness** (`eval/`) — a runner-agnostic test suite that installs Mano into a throwaway project, invokes a skill headless (claude / codex / opencode), and asserts on the files it produces. Run with `npm run eval`. Ships with format, behavioural, and refusal assertions plus fixtures for `mano stories` and `mano import`. This retires the "no automated test/eval suite" limitation noted in 1.0.0.
- **`post-import` hook** example, for parity with the other skills.

### Changed
- **Intake Boundaries (B1–B4)** now live canonically in `workflow.md`, shared by `mano start` and `mano import` instead of being duplicated. One source of truth, no drift.
- **Skills slimmed** — `mano start` (Path C extracted), `mano stories` (intake simplified, redundant test/Implementation-Reference prose cut, the story index drops its Description column), and `mano review` trimmed. Less context loaded per run.
- **`mano review` no longer manages story state** — if stories aren't `done` it refuses and points to `mano dev` or a manual README edit, rather than marking or cutting stories itself.

### Fixed
- **`mano review` double-confirm** — saying "all valid, close it" in one message now closes the phase immediately instead of asking to confirm a second time.

## 1.0.0 — Initial Release: June 18, 2026

Mano started from a simple frustration: heavyweight AI planning frameworks ask you
to think everything through upfront, generate large documents, and trust agents to
run with them. Mano takes the opposite bet — that software rarely moves in a straight
line, so planning should stay cheap to revise and the human should stay the judge at
every step. It is a supervised, à la carte planning protocol for coding agents:
small shippable phases, only the context the current phase needs, and artifacts that
are explicit, human-readable, and disposable when they stop being useful.

This first release makes Mano installable and settles its core surface after a long
period of refinement against real projects.

### Key Features
- **À la carte, not a pipeline** — a minimal path of a few commands; every other
  planning action (`spec`, `ux`, `rules`, `ui`) is optional context-tightening you
  run only when the current phase needs it.
- **Phases as the unit of work** — each phase is scoped, built, reviewed, and closed
  as one coherent, independently verifiable slice, with the human approving at each seam.
- **A thin implementer contract** — `mano dev` implements one story against its
  acceptance criteria and stops; one-line output, no narrative, no scope creep.
- **Action-named skills** — `mano start`, `mano spec`, `mano stories`, `mano review`,
  and more, each a focused constraint lens that reads only what it needs.
- **`npx mano-plan install`** — one command drops Mano into any project; re-run it to update.
- **Token-efficient by design** — Mano loads one skill at a time rather than a whole
  pipeline, and keeps the implementer's per-story contract small, so the build loop
  spends its context on your code rather than on the framework.

### Limitations
- Single-threaded by design — one phase at a time; concurrent multi-team work on the
  same phase track isn't supported.
- No automated test/eval suite yet, so the framework's quality rests on human review.
- Behaviour depends entirely on the agent's instruction-following; smaller models can
  still drift, and the human remains the enforcer of scope and quality.
