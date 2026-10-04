---
name: mano-task
description: POC — implement exactly one existing backlog item directly, without creating or approving a phase. Use only when the user explicitly names a backlog item to implement.
requires: []
---

# `mano task "[backlog item title]"` — implement one backlog item directly

> POC skill. Not part of the Mano release; not referenced by `workflow.md`, `AGENTS.md`, or any other skill.

A user may explicitly request implementation of one existing backlog item without creating or approving a phase.

This file is the complete contract. It carries its own copies of the `mano dev` / `mano build` readiness and done gates, adapted from a story to a backlog item. Do not load `_mano/rules/implement.md` as well: its phase-scope gate assumes a phase brief, and here there isn't one.

## Language check — before any response

Run `node _mano/scripts/settings.js language` from the project root before the first user-facing message or any project write. Use `language.chat` for conversation and `language.build` for code, tests, and product text. If the command fails, report the failure and stop.

## Steps

1. **Find the item.** Open `_mano_output/backlog.md` and locate the item whose `###` title matches the user's request exactly. If there's no exact match, or more than one, stop and list the closest titles. Do not guess.
2. **Check it's open.** Its `**Status:**` must be `backlog`. If it's `in-phase-*`, `resolved`, or `rejected`, stop and say so. An `in-phase` item belongs to its phase and is implemented through `mano dev` / `mano build`.
3. **Gap types are not implementable here.** A `spec-gap`, `rule-gap`, `ux-gap`, or `ui-gap` item is a decision owned by `mano spec` / `rules` / `ux` / `ui`. Stop and route it there.
4. **Read project context before you change anything:** the item's context, the artifacts it names, and `_mano_output/project-rules.md` for the area you'll touch. Then read source.
5. **Run the readiness gates (R1–R4) and the escalation check.** If any of them stops you, stop before you edit anything.
6. **Implement exactly this item** (see Rules).
7. **Verify.** Run every build, lint, type-check, and test command through `node _mano/scripts/verify.js -- <command>`. If a failure's fix is inside this item's scope, fix it and re-run. Otherwise stop, report the failure, and leave the status alone.
8. **Run the done gates (D1–D2).** Only when both pass, change only that item's `**Status:**` line from `backlog` to `resolved`, and leave every other line in `backlog.md` untouched. (`backlog.js` has no command for this yet, so edit that one line by hand.)
9. **Report** (see Output).

## Readiness gates — before any edit

A stop here means **no edits**: no source, no tests, no artifacts. The item keeps `Status: backlog`. Name the gate, quote what's missing, and name the owning command. Do not write the gap into `backlog.md` yourself; the human decides whether to record it.

**R1 — Checkable outcome.** A backlog item has no acceptance criteria, so its context has to stand in for them. Before code, write down in one or two lines the observable outcome this item delivers: what a user, test, or caller can see happen once it's done. Every part of that outcome must come from the item's context or an artifact it names, not from what you'd expect such a feature to do. If the context can't support a checkable outcome (e.g. "improve the inventory", "polish combat"), stop: the item needs scoping → `mano start`.

**R2 — Spec-owned default gap.** If the item needs a starting state, first-use state, capacity, radius/range, count, duration, threshold, spawn amount, or other behaviour-driving default, a canonical spec section must state the owning field/config/constant and its exact value or relationship. A vague phrase such as "small area" is not an implementation value. If it's missing, stop → `mano spec "[the item title]: [each missing value, named]"`. `mano spec` writes a directive like that into `tech-spec.md` with no phase and no backlog row. Do not choose a default yourself, add a temporary literal, or treat a test fixture as the product default.

**R3 — Player-choice UX gap.** If the item lets a player choose among two or more simultaneously available tools, buildables, abilities, modes, rewards, or alternatives, `_mano_output/ux-flow.md` must define how the player invokes the choice, selects/changes the active option, sees that active state, and receives locked/unavailable/cancel feedback. If it doesn't, or the file doesn't exist, stop → `mano ux "[the item title]: [the choice that needs a flow]"`. Do not invent a hotkey, picker, cycling scheme, default active item, or HUD treatment.

**R4 — Tech-spec pre-read.** If the item is setup, tooling, infrastructure, or dependency work, or involves user-entered or local data, read `_mano_output/tech-spec.md` first.
- Library choices, the package manager, and install commands there are normative. Run install commands exactly as written; don't merge, reorder, or switch tools.
- Never run a project generator against the project root, and never move, rename, or delete existing files to make room for one. If the item needs one and the tech spec has no guarded `node _mano/scripts/scaffold.js run ...` command for it, stop → `mano spec "[the item title]: scaffold command"`.
- If the tech spec says the data persists across restarts, restart persistence is part of R1's outcome, not an extra.
- If the item needs a stack decision the tech spec doesn't make (a new library, storage, or service), stop: escalate (see below).

## Escalate instead of implementing when

- the task requires a significant architecture decision
- requirements are materially ambiguous
- implementation would affect multiple major systems
- the task conflicts with existing project rules
- completing it requires substantial work outside the backlog item

In those cases make no edits and leave the status `backlog`. Name the trigger in one line, then recommend creating a phase: `mano start` with this item.

## Rules

- The backlog item must already exist.
- Implement exactly one backlog item.
- Read existing project context before implementation.
- Do not create a phase brief, stories, or a `progress.md` ledger.
- Do not expand the scope of the backlog item.
- Do not implement adjacent backlog items, even when they touch the same code.
- Do not introduce new architecture unless the item requires it.
- Do not add dependencies unless the item requires them.
- Follow existing architecture and project rules.
- Run relevant tests/checks.
- Update the backlog item status when complete.
- Report anything discovered that belongs in another backlog item. Report it only. Do not add it to `backlog.md` unless the user approves; once they do, use `node _mano/scripts/backlog.js add`.

## Done gates — before the status may become `resolved`

A failure here leaves the status `backlog` and is reported. Keep the edits, and say they're partial.

**D1 — Outcome evidence.** Reread the outcome you wrote for R1. For every part of it, point to concrete evidence from this turn (a test that exercises it, or a manual/runtime check you ran) showing the outcome happens through the route the item describes. A green suite is not enough if nothing in it exercises the outcome. Any assertion, fixture, comment, skipped test, or observed result that says the opposite (success expected as failure, available expected as unavailable) proves the item is **not done**, even if everything passes. If current code or an artifact deliberately keeps the opposite behaviour, stop and report the contradiction; do not invert the test or reword the outcome to match. If a visual or experiential part can't be checked, report it as unverified and don't resolve.

**D2 — Design-contract conformance.** If the item produced or changed a user-visible surface and `_mano_output/design-brief.md` names components for that surface, confirm from **this turn's edits** that the surface uses each named one: its name, or the file that defines it, appears in what you wrote. A shared theme, matching colour, copied style, or hand-built lookalike is not the component. A missing one means not done.

## Output

```
[mano task]: <item title> → resolved
Outcome: <the R1 outcome, one line>
Changed: <files>
Checks: <verify.js PASS lines>
Discovered (not added): <one line each, or "none">
```

When a readiness gate stops or escalation fires (no edits made):

```
[mano task]: <item title> — not implemented
Why: <R1/R2/R3/R4 or escalation trigger> — <what's missing, one line>
Next: <mano start | mano spec "<item>: <what's missing>" | mano ux "<item>: <what's missing>">
```

When a done gate or verification fails (edits kept, status unchanged):

```
[mano task]: <item title> — partial, still backlog
Why: <D1/D2 or failing check> — <one line>
Changed: <files>
```
