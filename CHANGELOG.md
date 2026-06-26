# Changelog

A history of Mano's releases — what each version changes and why.

## 1.1.1 — June 26, 2026

### Fixed
- **Install no longer overwrites or silently skips existing bootstrap files** — `AGENTS.md`, `CLAUDE.md`, and `.cursorrules` previously were written only if absent and skipped entirely if present, so installing into a project that already had an `AGENTS.md` never added Mano's instructions. The installer now fences Mano's content in `<!-- MANO:BEGIN -->` / `<!-- MANO:END -->` markers and: writes the file if it doesn't exist, **appends** the Mano section if the file exists without one (preserving your content), **skips** if a Mano section is already present (idempotent re-install), and with `--force` replaces only the fenced Mano block rather than the whole file.

## 1.1.0 — June 26, 2026

### Added
- **`mano import`** — a dedicated skill that turns an existing PRD or document into a backlog, then stops. Decomposition logic (the central-noun gate, resolution test, pre-send filter) moved out of `mano start`'s PRD path into its own command. Run `mano import <doc>`, review the backlog, then `mano start` to scope the first phase.
- **Eval harness** (`eval/`) — a runner-agnostic test suite that installs Mano into a throwaway project, invokes a skill headless (claude / codex / opencode), and asserts on the files it produces. Run with `npm run eval`. Ships with format, behavioural, and refusal assertions plus fixtures for `mano stories` and `mano import`. This retires the "no automated test/eval suite" limitation noted in 1.0.0.
- **`post-import` hook** example, for parity with the other skills.

### Changed
- **Repositioned around the planning loop** — the README and npm description now lead with Mano as *"a fast planning loop: plan in small phases and validate each assumption before it becomes code, with the human in control at every step."* The token-efficiency framing is demoted to a scoped greenfield note rather than a headline claim.
- **Intake Boundaries (B1–B5)** now live canonically in `workflow.md`, shared by `mano start` and `mano import` instead of being duplicated. One source of truth, no drift.
- **Skills slimmed** — `mano start` (Path C extracted), `mano stories` (intake simplified, redundant test/Implementation-Reference prose cut, the story index drops its Description column), and `mano review` trimmed. Less context loaded per run.
- **`mano review` no longer manages story state** — if stories aren't `done` it refuses and points to `mano dev` or a manual README edit, rather than marking or cutting stories itself.
- **`mano start` drops the redundant brief confirmation** — once you've approved the phase scope and answered the clarifying questions, it drafts the brief, writes it, and stamps the backlog in one turn instead of pausing again to ask "happy with the draft?". The brief is shown immediately; edit the file or re-run if anything's off.

### Fixed
- **`mano review` double-confirm** — saying "all valid, close it" in one message now closes the phase immediately instead of asking to confirm a second time.
- **`mano stories` no longer edits input artifacts** — when you point out the phase brief (or any input) has a stale/incorrect assumption, it now uses the correction to generate the stories and flags the staleness for the owning skill, instead of editing the brief itself. The no-implementation gate now explicitly covers other Mano artifacts, not just source code.
- **Intake no longer mines source code to scope (new boundary B5)** — `mano start` and `mano import` scope from planning artifacts and your answers, not by reading the codebase to enumerate the work list or verify defects. A quick structural glance to ground a scoping question is still allowed; building the missing-work inventory from source is now forbidden and left to `mano stories`. Applies even to "document/refactor the code" phases.
- **Command dispatch: hyphen, not colon** — `mano import` (and any `mano <action>`) now reliably resolves to the `mano-import` skill. Agents were transforming the spaced form into `mano:import` (plugin-namespace syntax), which matches no Mano skill and made the command look unavailable. Dispatch rules in `workflow.md`, `AGENTS.md`, and `CLAUDE.md` now state the separator is a hyphen and tell the agent to try `mano-<action>` before concluding a command doesn't exist.
- **Backlog item format inlined where it's written** — `mano import` invented a non-standard backlog shape (`**ID:** / **Title:** / **Description:**`) because it only *referenced* the format defined in `mano start` instead of containing it. The exact item block (`### title`, `**Type:**`, `**Source:**`, `**Context:**`, `**Status:**`) is now inlined in both `mano import` and `mano review`, with an explicit "do not invent fields" guard. This matters because `mano start` parses these items later — mismatched field names make them unreadable.
- **`Source` is now optional in backlog items** — it's provenance only and no skill reads it, so hand-added items can omit it instead of inventing a value. `Type`, `Context`, and `Status` remain required. Skills that auto-write items still fill `Source` when it's obvious (the document name, the review phase).

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
