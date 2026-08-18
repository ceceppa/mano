---
name: implement
description: The implementation contract shared by mano dev and mano build — the gates that run before code, the acceptance-evidence gate, Repair Mode, the read budget, and output discipline.
---

# Implementation contract (shared)

Shared by the two skills that produce code: `mano dev` (one story) and `mano build` (one Scope row of the phase brief). Both name this file in `requires:`. Read it once, immediately after the skill's own contract and before the state projection — it is identical on every run, so that order keeps the prompt prefix cacheable.

One implementation contract, two units of work. Where this file says **the unit**, read:

| | `mano dev` | `mano build` |
|---|---|---|
| the unit | the story file | the numbered `## Phase Scope` item the ledger row addresses |
| its acceptance criteria | the story's `Done when` | the phase brief's `## Exit Criteria` leaves the unit can satisfy |
| its implementation reference | the story's `Implementation Reference` section | derived in-turn from the artifacts, never written to disk |
| the status write | `stories.js set-status` (dev step 11) | `progress.js set-status` |

Step numbers are stable across both paths and are cited by name elsewhere in Mano — do not renumber them.

## Before writing code — the gap gates

6.2 **Spec-owned default gap.** If the unit or its cited phase Exit Criterion needs a starting state, first-use state, capacity, radius/range, count, duration, threshold, spawn amount, or other behaviour-driving default, the named canonical spec section must state the owning field/config/constant and exact value or relationship. A vague phrase such as “small area” is not an implementation value. Stop and route to `mano spec` when it is missing; do not choose a “story-owned default,” add a temporary literal, or treat a test fixture as the product default.
6.3 **Player-choice UX gap.** If the unit lets a player choose among two or more simultaneously available tools, buildables, abilities, modes, rewards, or alternatives, the cited UX flow must define how the player invokes the choice, selects/changes the active option, sees that active state, and receives locked/unavailable/cancel feedback. If it does not, stop and route to `mano ux`; do not invent a hotkey, picker, cycling scheme, default active item, or HUD treatment while implementing.
6.4 **Phase-scope conflict.** Before changing code, compare the unit and any user-requested behaviour change with the exact projected phase brief's `Phase goal`, `Phase scope`, and `Not this phase`. Work that directly supports an existing outcome can proceed. A distinct outcome, or anything the brief explicitly excludes, is outside this phase: stop before code. Do not treat “do it anyway” as permission to leave the brief stale. Ask the human to either defer it to the backlog/next phase or amend the phase brief to include it, then rerun `mano stories` to create or update the bounded story — on the build path, resume `mano build` against the amended brief instead. This gate applies in default, YOLO, and auto mode.
7. If the unit is bootstrap, setup, tooling, infrastructure, or dependency-related, also read `_mano_output/tech-spec.md` before implementing. Treat library choices, package-manager choice, and install commands there as normative unless the unit's own text already repeats them exactly.
8. Execute install commands exactly as written. Do not merge separate command groups, switch tools, or normalize mixed-tool instructions into a single package-manager invocation unless the unit or the tech spec explicitly tells you to. In particular, keep `npx expo install` commands separate from `npm install` or other package-manager commands so Expo can resolve SDK-compatible versions.

   **Greenfield scaffold safety is a hard stop.** A project generator that creates an application root or requires an empty destination may run only through the exact guarded command in `_mano_output/tech-spec.md §Project Scaffold`: `node _mano/scripts/scaffold.js run ... -- ... {target}`. Never aim a raw generator at `.`, the project root, or a temporary child that you later merge by hand. Never move, rename, delete, or temporarily hide existing files to make the root look empty—especially `_mano`, `_mano_output`, `.git`, `AGENTS.md`, `CLAUDE.md`, or `.cursorrules`. Do not substitute `cp`, `mv`, `rsync`, or a hand-written merge. If the guarded command is absent, malformed, fails, or reports a collision, stop and report it; route an absent/malformed command to `mano spec`, and never improvise around a runner failure. `yolo` and auto mode do not relax this rule.
9. If the unit involves user-entered state, forms, onboarding drafts, settings, or other local data, check whether the unit or the tech spec says that data should persist across app restarts. If it should, treat restart persistence as part of the required behaviour, not as an optional enhancement.
10. Read `_mano_output/project-rules.md` only when the unit explicitly points to a rule there, something remains ambiguous after reading the unit and any mandatory tech-spec pre-read, or you need fuller context behind a rule already summarized in the unit.

    **Verification runs filtered.** Run every build, lint, type-check, and test command for verification through `node _mano/scripts/verify.js -- <command>`. On success it prints one `PASS:` line; on failure it prints the trimmed error excerpt. Do not run verification commands raw and paste their full output into the conversation. A failing verification enters **Repair Mode** (below).

## After implementing — the acceptance-evidence gate

<!-- mano-rule: id=phase-acceptance-integrity; incident=exit-criterion-tested-in-reverse; model=codex; date=2026-08-13; eval=pending -->
10.1 **Acceptance-evidence gate — before status may become `done`.** After implementation and verification, reread the unit's complete acceptance criteria. For every one of them, identify concrete evidence from this turn that the stated outcome occurs through the stated route. A passing suite is not enough when no test/manual check exercises that AC. Any assertion, fixture expectation, comment, skipped test, or observed result that states the opposite outcome—success expected as failure, recoverable expected as locked, available expected as unavailable—is proof the unit is **not done**, even if the suite is green.

When an AC cannot be satisfied because current code or a cited artifact deliberately preserves the opposite behaviour, stop before the status write, leave the row pending, and report the contradiction. Route a planning-contract contradiction to `mano spec`/`mano stories` as appropriate; do not rewrite the AC's meaning, invert the test, call the opposing behaviour intentional, or mark the unit done with a deviation. For an AC that is inherently visual or experiential, perform the narrow available manual/runtime check; if that cannot be run, report the unverified AC and leave the row pending.
<!-- /mano-rule: phase-acceptance-integrity -->

## Repair Mode

A failing build, lint, type-check, or test during verification enters Repair Mode. Fixed budget; never widen it.
Use, and nothing else: (1) the FIRST error only — discard passing lines, banners, later errors; (2) for each
file:line in that error not already read this turn, a ±12-line window (`sed -n`), not the file; (3) the unit's
acceptance criteria and implementation reference, already in context.
Never: re-read the unit/brief/spec/rules (they didn't change); re-read any file already read this turn; paste
full command output (report the error's first line); rewrite a class or file to fix one assertion — repairs are
surgical edits at the failure site; run the full suite to check a fix — re-run the narrowest reproducing command,
full suite exactly once after it passes.
Repair-mode commands still run through `node _mano/scripts/verify.js -- <command>` — it already reports the
trimmed failure excerpt.
Attempt limit: 3 on the same error → stop, leave the row pending, report ≤3 lines (error, file:line, tried).
Exception — never optimised away: the `state.js` re-check before the status write, and the
acceptance-evidence gate (10.1), run in full regardless.

## Read budget

Read source in the smallest useful unit: signatures and declarations first (search/grep), then narrow line ranges around the edit site. Open a full file only when you are editing it and it is small. Do not preload artifacts or source "for context" beyond what the unit's implementation reference names.

## Implementation Output Discipline

The implementing agent writes code and updates the unit's status. It does not append completion reports, verification logs, behavioural confirmations, or implementation narratives to the story file or the ledger.

It also does not print these to chat. After implementing, the only required chat output is the skill's own single closing line — dev step 12, or build's report from the ledger. Do not restate acceptance criteria, list "AC Met", enumerate created files, or write an implementation summary. The acceptance criteria already live in the story or the brief; echoing them back adds no information and only grows the conversation. Report only non-acceptance deviations or follow-up that did not weaken any AC. An unmet or unverified AC leaves the row pending under step 10.1. If there are no such notes, the one-line confirmation is the complete response.

If implementation produces project-relevant decisions worth preserving — colour values, dimensions, performance budgets, accessibility measurements, architectural patterns, technique choices, library quirks discovered in practice — the agent surfaces them in chat and offers to capture them in the appropriate artifact:

- Architectural or repeatable conventions → `_mano_output/project-rules.md`
- Visual or design decisions → `_mano_output/design-brief.md`

The story file and the phase brief remain planning artifacts, not implementation logs. This applies to all implementing agents, including third-party language specialists and external coding skills.
