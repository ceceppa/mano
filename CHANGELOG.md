# Changelog

A history of Mano's releases — what each version changes and why.

## 1.3.0 — August 10, 2026

### Added
- **`mano mode auto|manual` adds an explicit, local hands-off option** — `manual` remains the default. After the human approves a phase scope, auto mode runs the approved, phase-specific planning chain through `mano dev yolo`, pauses for every human decision or blocker, and always stops before `mano review` or another phase. The mode lives in repository-local Git config, can be overridden with `MANO_MODE`, and is projected by every `state.js` view, including gap-only and JSON output.
- **Hooks now support deterministic `command` mode** — a command hook names one project command that runs after its skill in both manual and auto modes. Existing and mode-less hooks remain `suggest`: Mano asks before running them in manual or unarmed work, while an approved auto chain runs them as the substitute for skipped intermediate human review and pauses if their findings need triage.
- **Exact backlog items can be pulled into an open phase through `mano stories`** — when the human names an existing item and it fits the already-approved goal, stories may assign that exact title with the backlog writer and add a lettered story. It cannot choose work, hand-edit the backlog, broaden the phase goal, or bypass the normal readiness gates.

### Changed
- **Auto chains are approved run plans, not repeatedly guessed next steps** — `mano start` performs a narrow project-artifact check before proposing the chain, preserves its ordered remaining actions across pauses, refreshes mode at each handoff, and resumes in the same turn after an answer is captured. New evidence can still pause or invalidate the plan; the agent never answers a fork for the human.
- **New repeatable artifact categories keep `mano rules` visible** — a phase that introduces a recurring file, module, component, document, example, or asset shape is treated as new rule territory even when a substantive rules file already exists.

### Fixed
- **Auto hook semantics no longer contradict themselves across skills and templates** — workflow, bootstrap instructions, every Mano skill, hook documentation, and example hooks now agree on manual suggest, auto suggest, and always-on command behavior.
- **`mano dev yolo` and auto-mode summaries no longer have incompatible output contracts** — standalone YOLO still emits exactly one aggregate line; as the terminal auto action, that line is followed only by the required auto closing block.
- **Paused chains no longer lose their continuation state** — the closing block records `Remaining:` actions, decision answers become mid-chain logs when appropriate, and switching to manual while paused cleanly hands control back instead of continuing from cached mode.
- **The mid-phase assignment path no longer conflicts with stories' write boundary** — the hard no-implementation gate and Forbidden section now name the single writer-mediated backlog exception while continuing to reject every direct or unrelated artifact edit.

## 1.2.0

### Added
- **Phase ownership is available as an explicit team opt-in** — existing projects continue to use `phase-N` unchanged. `mano owner <slug>` stores a non-committed local owner and routes phase-scoped state, backlog statuses, stories, previews, development, and reviews through `<owner>-phase-N`; numbering and lifecycle gates are independent per owner. Clearing the owner returns to legacy routing without renaming artifacts, and two developers can select the same slug for hand-off. Shared project artifacts still require ordinary branch/worktree and merge coordination.
- **`mano dev yolo` is now an explicit batch exception** — ordinary `mano dev` still implements one story and stops, while the literal `yolo` modifier processes the stories pending at invocation sequentially in index order. Each story keeps its own acceptance criteria, scope boundaries, verification, and immediate status checkpoint; the batch stops at the first blocker and never auto-reviews, advances phases, commits, or pushes.
- **Incident-backed rules can now be tested for retirement** — paired provenance markers begin a deliberately partial inventory of the real incident, observed model, date, and mapped evals. `npm run eval:rules` lists the tagged subset, while `eval/run.py --probe-rule <id>` removes every occurrence only from throwaway installs and runs all mapped surfaces. `npm test` validates the marker, coverage mapping, and stripping contract without invoking a model.
- **Gap work now has a narrow script interface** — `state.js --gaps spec-gap|rule-gap` exposes only unresolved items of the requested exact type, while `backlog.js resolve-gap` safely resolves one exact, type-checked item after its owning skill addresses it.

### Changed
- **Public interface contracts are checked before stories reach development** — `mano spec` now receives the exact source backlog items already assigned to the human-approved phase, distinguishes consumer-visible or independently-owned contracts from local implementation APIs and project-wide signature conventions, reconciles named brownfield declarations, and verifies operation names, inputs/defaults, results/failures, ownership/timing, and semantic mappings. Its projection is self-delimiting and fails closed on truncation or an active phase with no backlog. `mano stories` blocks incomplete qualifying contracts instead of leaving them for `mano dev` to invent.
- **UI previews are now owned by their phase** — `design-brief.md` remains the cumulative project-wide visual contract, while `mano ui` writes the current demo to `phase-[N]/design-preview.html`. Later phases preserve prior previews, same-phase re-runs may update their own preview, and legacy root previews are left untouched instead of being silently reassigned or overwritten.
- **The scripts are a hard requirement — the no-Node hand-edit fallbacks are gone.** Every "No Node / script missing? do it by hand" escape hatch has been removed: if `state.js`, `backlog.js`, or `stories.js` cannot run, the skill stops and reports the exact failure instead of hand-writing a script-owned format or re-deriving the state projection by scanning. Mano is installed with `npx`, so Node is present by construction; the fallback was a drift channel — any script error became a license to do exactly the hand-editing the writers were built to eliminate. The rule lives canonically in `workflow.md` ("Scripts are mandatory"); sanctioned hand-edits (Core Product Principles, split title/context edits, the follow-up review's title-scoped resolves, the user's own edits) are unchanged.

### Fixed
- **Applicable project rules can no longer disappear during story decomposition** — `mano stories` now maps every applicable rule to an owning story before writing. Implementation constraints become explicit `Implementation Reference` obligations, required companion outputs such as documentation pages become `Done when` criteria, and cross-cutting work gets an ordered dependent story when it cannot fit coherently in the introducing story. A phase brief that excludes something a project rule requires is surfaced as an artifact conflict instead of silently weakening the rule.
- **`mano spec` and `mano rules` no longer need the full backlog** — each skill consumes a narrow projection and is explicitly forbidden from opening `backlog.md`; spec receives active-phase items plus spec gaps, while rules receives rule gaps. Both use the targeted writer instead of hand-editing statuses. Gap-only items remain excluded from `mano start` readiness and scope output, so they route to their owning skills instead of producing an empty phase suggestion.
- **Post-hook findings now have a human-approved return path** — after `post-start`, `post-spec`, or `post-rules` reports findings, the owning skill presents a compact apply / decide / route triage and waits for explicitly numbered selections. It never bulk-applies reviewer output, silently reconciles artifact conflicts, edits across ownership boundaries, or persists a findings ledger; `post-stories` retains its stricter immutable-story protocol.
- **Eval runner failures and tool traces can no longer produce false passes** — a non-zero model process now fails its case even when unchanged fixture files happen to satisfy an assertion, and chat-native assertions inspect each runner's isolated last assistant message rather than stdout/stderr traces. OpenCode runs with an explicit temp-project directory and no external plugins, expected fixture text is snapshotted before invocation, and any escape that mutates a repository fixture is reported as an isolation failure.
- **Review closure is enforced consistently** — `AGENTS.md`, `mano dev`, `mano start`, and `state.js` now agree that all stories being `done` means built, not closed; only `mano review` permits the next phase, interrupted backlog close sweeps have a repair path, and a missing requested story no longer makes a phase with other pending work look complete.
- **Existing story sets are protected on re-run** — `mano stories` reads the current index before writing, never regenerates a set without a concrete change request, preserves `done` stories, and lettered insertions go through the index writer.
- **Writer and boundary wiring matches the shared contracts** — `mano import` uses `backlog.js`, the writer enforces its five-line context limit, `mano ui` no longer reads the backlog or edits project rules, and routine spec re-runs update in one shot without an extra confirmation gate.
- **Eval coverage now exercises failure paths** — the import fixture satisfies its mandatory central-noun gate, assertions verify exact contract text more closely, and new cases cover pending-review refusal and immutable mid-build story insertion.
- **Stale cross-references cleaned up** — the workflow help table no longer claims `mano ui` reads the backlog; `mano spec` no longer points at the removed `⚙️`-row diff format; `post-import` appears in every hook example list; the installer/README/AGENTS.md docs now mention `_mano/scripts/`; and leftover doubled skill-name phrases from the persona removal ("that's `mano start`'s job via `mano start`") read normally again.

## 1.1.2 — June 29, 2026

### Added
- **`LICENSE` (MIT)** — the package already declared `"license": "MIT"` but shipped no license text. npm always includes a `LICENSE` file in the tarball, so the published package now carries the full license. No functional change to `npx mano-plan install`.
- **`CONTRIBUTING.md`** — a contributor guide covering what Mano is (skills-as-prompts, no runtime engine), the bar a change must clear (lower the human's cost per decision, keep the human in the loop, be backed by a real incident, stay un-opinionated and stack-agnostic), the repo layout, and the eval/shrink-a-persona workflow. GitHub-facing; not shipped in the npm tarball.

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
