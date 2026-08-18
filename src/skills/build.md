---
name: mano-build
description: Use to build the active phase straight from its brief, tracked in a progress.md ledger — no story files. Read this file and _mano/rules/implement.md fully before writing any code.
requires: [implement]
---

# `mano build` — build the phase from its brief

This file plus `_mano/rules/implement.md` are the **complete contract** for `mano build`. Read both completely before writing any code, including when the user asks in plain words ("now build the phase"). Together they are self-contained: no other `_mano/` file is required, and `_mano/workflow.md` is never opened mid-skill.

**The unit of work is the numbered `## Phase Scope` item the human already approved** — not a unit this skill invents. That single property is what the rest of this file protects. A row that is a copy of the brief cannot drift from it, so build needs no story format, no filename law, no acceptance-criteria authoring, and no quality rules for text it never writes. What it does need, unchanged and in full, are the gates that decide whether the brief is ready to build at all.

`mano build` is one of two paths and replaces neither. `mano stories` + `mano dev` stay first-class: they split planning (big model) from implementation (small model) and suit a large phase. `mano build` runs one phase in one contract on one model, checkpointed by a ledger. One phase uses one path — a phase holding both `stories/README.md` and `progress.md` is refused by the state projection.

**Read order — keep the prefix stable.** Read this contract and `_mano/rules/implement.md` first (they are identical on every run, so they cache as a stable prompt prefix), then the state projection, then the phase brief, then the artifact sections a row needs, then source.

**No free-text argument.** `mano build "add dark mode"` is rejected: an argument is a channel for scope the brief does not contain, and this whole design rests on the ledger being derivable from the brief alone. Refuse the argument and stop: say that work outside the brief goes through `mano start` (or the backlog), and that a plain `mano build` builds the brief as written. Do not run the argument's work, do not append a row for it, and do not proceed into the ledger in the same turn. A correction *typed into a running build* is different and has its own protocol — see **Mid-phase corrections**.

## Flow

**0. Find what to build by running the state script — do not `ls` for the phase or infer it from the conversation.** Run `node _mano/scripts/state.js --next`. It reports `MODE`, the selected `OWNER`, exact `PHASE_ID`, numeric `PHASE`, `PHASE_DIR`, `BRIEF`, `PROGRESS`, both ledger tables, and the next non-`done` row. If `MODE` or any routing field is absent, stop and report the malformed projection. Obey its `OWNER`/`PHASE_ID`/paths; never construct `phase-N` from the number. **If the script cannot run, stop and report the exact failure** — do not scan for the phase by hand. If it reports no phase or no brief, follow the line it prints and stop.

**1. No ledger yet (`PROGRESS_STATUS: missing`) → read the brief and run pre-flight once, against the whole brief.** This is the cheapest place in the whole phase to catch a gap: nothing has been written and nothing has been built. Run **Step 0 pre-flight** below. A hard gate or an unresolved artifact gap **stops the run and writes no ledger** — route it to the owning skill and stop.

Then create the ledger with one command. It takes no content:

```
node _mano/scripts/progress.js init --phase [N]
```

`[N]` is the numeric `PHASE` from the same projection. The script reads the brief and emits both tables itself — a Scope row per `## Phase Scope` item, an Exit Criteria row per `## Exit Criteria` leaf. **You never pass rows in and never hand-write the ledger.** If `init` refuses because a section has no list to parse, that is the brief's shape, not something to work around: report it and route to `mano start`. Then run the **Exit-criteria coverage check**.

**2. Implement in row order.** For each row, in the order the ledger lists it:

  a. Flip it to `doing`: `node _mano/scripts/progress.js set-status --phase [N] --row [id] --status doing`.
  b. **Read the brief's item at that number** — the ledger cell is a scannable handle, the brief's text is the contract. Derive what the row needs from the artifacts *in this turn*; never write an implementation reference to disk. It is expensive, single-use, and wrong to persist.
  c. Apply gates **6.2**, **6.3**, **6.4** and the **read budget** from `_mano/rules/implement.md`, then implement, then verify through `node _mano/scripts/verify.js -- <command>`, then apply gate **10.1**.
  d. Flip the row `done` and mark `met` every Exit Criterion this turn produced evidence for, in one call:
     `node _mano/scripts/progress.js set-status --phase [N] --row [id] --status done --row [Eid] --status met`
     No stored row → criterion mapping exists and none is needed: mark leaves as the evidence appears, and step 4's terminal gate requires all of them regardless of which row got there. A leaf you cannot yet prove stays `pending` — that is the gate doing its job.
  e. Re-run `state.js --next` and confirm `OWNER` and `PHASE_ID` are unchanged and the row now reads `done`. Stop without claiming progress if either postcondition fails.

**3. Stop when this turn's output budget is spent.** Report from the ledger (see **Chat output**) and stop. **Resume in a fresh session**, not by continuing this one: a fresh session restarts residency and reads back the exact position for a few hundred tokens, while continuing carries every message you already paid for. A resumed run starts at flow step 0 and picks up the first non-`done` row; it does not re-derive completed rows.

**4. Terminal — every Scope row `done` and every Exit Criterion `met`.** Output one aggregate line and stop. The phase is **built, not closed**: `mano review` is mandatory and unchanged. Do not scope, plan, or start another phase. If every Scope row is `done` but some criterion is still `pending`, the phase is *not* built — prove the remaining leaves, or reopen the row that owes the evidence.

## The ledger

`PHASE_DIR/progress.md` is the phase's durable state: the decomposition and the status, nothing else. It survives compaction, session end, and interruption, which is why it is a file and not something you hold in the conversation. `state.js --next` routes from it, `mano review` gates on it, and a fresh session resumes from it.

- **The number is the contract; the label is decoration.** `S2` addresses `## Phase Scope` item 2 in the brief, and *that text* is what you implement against. `E2b` addresses category 2, leaf b of `## Exit Criteria`.
- **Never hand-write or hand-edit the ledger.** Every change goes through `progress.js` (`init`, `set-status`, `split`, `add-row`). A hand-written approximation of a script-owned format is exactly the drift the script exists to make impossible. If the script fails, stop and report the exact error.
- **Two status vocabularies, deliberately distinct.** Scope rows: `pending | doing | done`. Exit Criteria: `pending | met`. **Built is not proven** — the script rejects `met` on an `S` row and `done` on an `E` row.
- **Row text is immutable; row status is correctable.** No row's text is ever rewritten. A status may move backwards when a defect surfaces, and that always requires an explicit `--reopen` and always fires the **deviation stop**.
- **Build never edits the phase brief**, or any other artifact it does not own — not to fix a typo, not to record what it built, not when the user says the brief is wrong. Reading an input artifact is how build works; writing to one is out of lane. `progress.md` is the one file build owns, plus the source it is implementing.

## Step 0 — pre-flight

Run these once, against the whole brief, before the ledger exists. Resolve each before moving on. A mid-phase correction re-runs 0c.0–0d against the new row (see **Mid-phase corrections**).

**0⊘. Ledger-and-source gate (hard stop).** The only files this skill writes are source code, the exact projected `PHASE_DIR/progress.md` (through `progress.js` only), and files a row's own work requires. If you are about to Edit, Write, or shell-modify **another Mano artifact** — the phase brief, tech spec, UX flow, design brief, project rules, backlog, or another owner's phase — **stop immediately**. That belongs to the skill that owns it. This applies even when the user just told you an input artifact is wrong: flag it and route it, do not edit it.

**0a. Overloaded screens.** If a UX flow screen handles more than two primary actions (excluding back/close/cancel/continue unless they perform mutation or branching), flag it before building. If `mano ux` has already split a flow into separate screens or steps, evaluate each step on its own. Create and edit for the same entity using the same underlying screen are not separate primary actions.

```
⚠️ [Screen name] handles [N] primary actions: [list them].
Options:
1. Run `mano ux` to split the screen.
2. Build it as one screen anyway.
```

Wait for the user's choice. On option 1, stop after the handoff message.

**0b. Supporting context report.** Report the inputs actually read from disk this run:

```
[mano build]: Read this run: [phase brief, tech spec, UX flow, design brief, project rules].
```

**0c. Readiness.** For each Phase Scope item involving mechanics, workflows, APIs, or stateful behaviour, verify: what data or entity does it operate on? what starts the behaviour? what state changes? what condition proves it worked? what default fixture, seed data, or example input is needed? If an item depends on missing domain structure, that is a gap — route it to `mano spec`; do not build around it with an invented model.

**0c.0 Spec-owned defaults and initial state — hard gate.** When an Exit Criterion or Phase Scope item depends on a starting state, first-use state, capacity, radius/range, count, duration, threshold, spawn amount, or other behaviour-driving default, verify the canonical tech spec names its owning field/config/constant and gives its exact value or required relationship. A brief may say “small healed area” or “enough room”; if code must turn that into a number, it is a technical decision, not story setup.

If that owner or value is missing, **write no ledger**. Report `⚠️ Build readiness gap: spec-owned default missing`, name the affected exit path and field that needs defining, and route to `mano spec`. Do not offer a build-owned default, a `TODO` in the code, or options to continue with a temporary value. Build may implement an already-decided default; it never chooses one.

**0c.1 Player choice interaction — hard gate.** When a player can choose among two or more simultaneously available tools, buildables, abilities, modes, rewards, or other alternatives, verify `_mano_output/ux-flow.md` defines the choice as a player path. It must cover what makes each option available, how the player enters or invokes the choice, how they select or change the active option, how the active choice is communicated, and what happens when an option is locked, unavailable, or the player cancels. The choice may be in-world or minimal; it is still UX.

If that flow is absent or leaves any of those decisions to implementation, **write no ledger**. Report `⚠️ Build readiness gap: player choice interaction missing`, name the affected phase path and missing UX behaviour, and route to `mano ux`. Do not propose a hotkey, picker, cycling scheme, default active item, HUD treatment, or other build-owned interaction. The general artifact-gap options do not waive this gate; only a completed UX flow or an explicit human decision to skip `mano ux` can do so.

**0c.2 Public-interface readiness — hard gate.** For every Phase Scope item that creates, changes, wraps, or depends on a public/package API, command, event protocol, plugin hook, external integration, persisted/wire format, or cross-component contract consumed by independently-owned components or multiple scope items, verify its canonical owning artifact defines:

- the exact consumer-visible operation, method, command, or event names;
- input order/shape, required vs optional values, and behavior-driving defaults;
- result/return or emitted payload plus validation/failure behavior;
- ownership/lifetime and evaluation timing for relative/lazy/dynamic values when they change consumer use;
- semantic-to-canonical mappings for convenience layers, adapters, aliases, serializers, or protocol translations.

For a fluent, builder, pipeline, query, or composed API, also trace every in-scope chain transition from the canonical spec: the exact returned type, the target/owner/context it retains, and which terminal operations remain callable. An Exit Criterion such as `builder.move(...).play()` does not prove `builder.move(...).with(...).play()` or `builder.keyframes(...).play()` unless the spec closes those return-type paths too. Words such as “any”, “all”, “entirely fluent”, and “combined” require coverage of every named category, not one representative leaf.

Apply this only to that consumer-visible or independently-owned boundary, not a private helper, internal service, or component API that one scope item and one implementer can safely design locally. “Supports position, movement, opacity, and generic properties” is not a callable contract: method names, argument shapes, and property mappings are still missing. “See tech-spec §API” is also insufficient when that section contains only the same family list. Verify every artifact section you are about to rely on: the exact operation and promised path must actually be present there.

If any behavior-driving interface field needed by a scope item is absent or has two materially different readings, **write no ledger**. Report one `⚠️ Build readiness gap` naming every missing field and route to `mano spec`. The general gap-check options to continue with a temporary note or partial guidance do not waive this gate; an implementer cannot safely invent a shared/public contract row by row.

**0c.3 Phase-promise polarity — hard gate.** Map every `Phase Goal` outcome and every `Exit Criteria` leaf to the Phase Scope item that will satisfy it and the supporting artifact decisions it needs. Read those decisions for meaning, not keyword presence. If any artifact states the opposite outcome or preserves a stale deferral (`recoverable` vs `stays locked`, `available` vs `unavailable`, `implemented` vs `not wired`, success vs required failure), **write no ledger**. Report one `⚠️ Build readiness gap: supporting artifact contradicts phase promise`, quote both statements, and route to the artifact's owning skill—normally `mano spec` for technical/data/gate contradictions.

**0d. Artifact gap check.** For each Phase Scope item, check whether it depends on a visual, interaction, accessibility, technical, data, API, constant, shared measurement, or rule detail that is not defined by the artifacts read this run. This is a warning/decision point, not a default blocker; the hard gates in 0c.0–0c.3 remain non-continuable.

**Player-flow check.** A game mechanic is not exempt from UX because it happens in the world rather than a screen. When the phase includes player activation, direct manipulation, placement/selection, progression/unlock actions, available-versus-locked states, or feedback for an unmet condition, check `_mano_output/ux-flow.md` for the concrete path: what the player notices, does, sees after success, and sees when the action is unavailable. Multiple simultaneously available choices are the hard gate in 0c.1, not a continuable artifact gap. “Minimal” presentation does not let build invent discoverability or feedback behaviour.

Look for partial-but-usable guidance before flagging a gap. A detail is not missing merely because it is brief. If an artifact contains a relevant section, subsection, token, note, rule, constant, or implementation reference, use it.

Flag a gap only when the missing detail would force the implementer to invent behaviour, visual treatment, data shape, API contract, accessibility semantics, or test fixtures that materially affect the story outcome.

When a gap is found, report it before writing the ledger:

```text
⚠️ Build readiness gap: [short gap name]

Affected scope item: [the brief's numbered item]
Missing guidance: [what is not defined]
Available guidance: [artifact references already found, or "none"]
Risk: [why this would cause guesswork or inconsistent implementation]

Options:
1. Pause and run `[relevant mano action]`
2. Continue with an explicit temporary note in the story
3. Continue using the available artifact guidance only
```

Use the relevant Mano action for the gap type:
- Visual treatment, layout, component appearance → `mano ui`
- Screen flow, interaction sequence, user decision path → `mano ux`
- Technical model, API, persistence, state ownership → `mano spec`
- Coding convention, accessibility enforcement, reusable implementation contract → `mano rules`

Do not invent final design, UX, rules, or technical contracts while building. If the user chooses to continue with a temporary note, record it in the chat log; never write it into an artifact you do not own.

**The options require a human answer.** After presenting a material gap, stop. Never choose option 2 or 3 yourself because the artifact is optional, the approved auto chain omitted it, the control is familiar/canonical, or enough implementation can be guessed. In an armed auto chain this is a named pause with the remaining chain preserved. Continue without the owning artifact only after the human explicitly chooses that path; an explicit `skip ux` / `skip ui` in the approved chain already counts as that choice.

If sufficient guidance exists, do not warn — read that section when you reach the row that needs it, for example:

`_mano_output/design-brief.md §EmptyState` for the visual spec, and the Colour Constants rule in `_mano_output/project-rules.md` for how to express it in code.

<!-- mano-rule: id=project-rule-story-coverage; incident=applicable-documentation-rule-omitted; model=not-recorded; date=2026-07-31; eval=stories-project-rule-coverage -->
A conflict between an applicable project rule and the phase scope is not a continuable artifact gap. Stop and apply gate 6.4; options 2 and 3 do not waive an existing rule.
<!-- /mano-rule: project-rule-story-coverage -->

**0e. Reachability.** For each Phase Scope item involving interactive behaviour, screens, endpoints, or any user-triggered action, name the surface it lives on, the action that invokes it, and how the user reaches that surface. Wiring that no item covers is a gap, not something to add silently — an unreachable feature passes its own check and ships as nothing the user can use.

<!-- mano-rule: id=project-rule-story-coverage; incident=applicable-documentation-rule-omitted; model=not-recorded; date=2026-07-31; eval=stories-project-rule-coverage -->
**0g. Project-rule coverage.** After the ledger exists and before writing code:

1. For every rule-level section in `project-rules.md` (normally each `##` rule, not its `What` / `Why` / `Pattern` parts), mark it internally as `not applicable` with a concrete reason, or `applicable` to one or more Scope rows. Decompose every normative obligation in `What` plus any explicit `must`, `required`, or `never` elsewhere: each bullet, required channel, `both`, and joined obligation needs its own mapping. Treat rationale and examples as interpretive context, not separate obligations. A single general pointer does not cover a compound rule.
2. For each applicable obligation, map it to the exact Scope row that must honour it, and to the Exit Criterion that proves it where one exists.
3. A rule-required outcome with a verification surface and no Exit Criterion covering it is a gap: report it and offer to add an `E` leaf (**Mid-phase corrections**, case C) rather than shipping it unproven.
4. If any applicable obligation has no row that can honour it, stop and report it — that is a gap in the brief, not something build fills in. If mapping exposes a phase-scope conflict, apply gate 6.4.

Do not write code until the map has no unmapped applicable obligations. Report the mapping only when it exposed a conflict or caused a row to be added; a clean map needs no narration.
<!-- /mano-rule: project-rule-story-coverage -->

## Exit-criteria coverage check

Run this **once, immediately after `init`**, against the two tables the script just emitted — before any code. It is an identity check between two human-authored lists, so it is cheap and it happens before anything is built:

1. Every Exit Criterion row must have at least one Scope row that could plausibly satisfy it.
2. Every Scope row must contribute to at least one Exit Criterion.

A mismatch is real information — the human's own brief is internally inconsistent — so it is a **deviation stop**, not something to reconcile by inference:

```text
[mano build]: The brief's Exit Criteria and Phase Scope don't line up:

- E2c "[criterion]" — no scope item ships the behaviour it tests
- S4 "[item]" — no exit criterion proves it

`mano start` owns the brief. Amend it there, or tell me which reading is right and I'll build to that.
```

Do not invent a scope item to cover an orphan criterion, and do not quietly widen a row to absorb one. Do not treat a `Not this phase` line as licence to drop a criterion.

## The human gate: stop on deviation only

Build runs straight through while the ledger is a copy of the human's own list — asking them to confirm their own approved brief carries no information and buys nothing. It **stops and asks** when, and only when, it deviated:

- pre-flight found a hard gate or an unresolved artifact gap (routes out, no ledger);
- the exit-criteria coverage check failed;
- gate 6.4 fired — the work conflicts with `Phase goal` / `Phase scope` / `Not this phase`;
- a sub-row split was needed;
- a row was reopened, or a correction row appended.

Every stop **names which condition fired** and shows the deviating text next to the phase goal. In an armed auto chain this is a named pause with the remaining chain preserved; do not answer on the human's behalf. The two standing gates never move: the human approves the brief at `mano start`, and `mano review` is mandatory at the end.

## Sub-rows: the one text build composes

When the row being built overflows this turn's output budget, and only then, record the split:

```
node _mano/scripts/progress.js split --phase [N] --row S2 --part "[the part already finished]" --part "[what remains]"
```

Three constraints, all enforced:

1. **Only for the row currently `doing`, and only after one part is genuinely complete.** The script refuses to split a `pending` row and records the first part as `done`, so build cannot pre-decompose. Pre-splitting the phase into sub-rows up front recreates story files with a worse format and throws away the entire saving.
2. **A strict partition of the parent.** No sub-row may introduce scope the parent does not already contain. The parent flips to `done` only when every sub-row is `done` — the script enforces that too.
3. **It fires the deviation stop.** Sub-row text is the *only* text in the ledger build composes itself: brief rows are parsed, correction rows carry the user's own words. So the human sees every one of them.

Dots are decomposition (`S2.1`), letters are corrections (`S2a`) — separate namespaces, never mixed.

## Mid-phase corrections

The user reports something mid-build. Classify it into exactly one of three cases. **The principle that makes this safe: the unit's text was written by a human.** A user's mid-phase instruction is human-authored text, exactly as trustworthy as a brief bullet. What must never happen is **build composing a row from its own inference**.

**(A) A defect in work already marked done — no new scope, no new row.** The code does not do what an existing `S` row or `E` leaf already requires. This is most mid-build reports, and it carries zero invention risk because nothing is authored at all. Reopen the affected rows and fix under them:

```
node _mano/scripts/progress.js set-status --phase [N] --row S2 --status doing --reopen --row E2c --status pending --reopen
```

The ledger was wrong: the row was never done, and gate 10.1 letting it through is the bug behind the bug. `--reopen` is mandatory and fires the deviation stop. Appending a new row for work an existing row already required is the error to avoid here.

**(B) A distinct outcome the phase does not contain — refused.** Gate 6.4 applies verbatim: stop **before** code, and route to `mano start` to amend the brief or defer it to the backlog. No row is appended, nothing is implemented. Auto mode does not soften this.

**(C) A nuance inside the phase goal that no row covers — appended as a lettered row.** It supports an existing outcome, but no `S` row or `E` leaf states it. Append the user's request:

```
node _mano/scripts/progress.js add-row --phase [N] --row S2a --text "[the user's own words, verbatim]"
```

Four constraints, all load-bearing:

1. **The text is the user's, verbatim.** Never paraphrase it into scope-ese, never compose it, never tidy it.
2. **The gap check runs against the new row before any code** — 0c.0–0d, then 6.2 / 6.3. If the addition needs a spec-owned default no artifact states, route to `mano spec` and **STOP**, exactly as at ledger creation. The row may exist; no code is written.
3. **The deviation stop fires**, showing the appended row against the phase goal, before implementation.
4. **A correction that should also be provable gets an `E` leaf** — `add-row --row E2e --text "…"` — or the phase can close with the fix unverified.

The boundary to watch is (B) misclassified as (C): new scope smuggled in as a nuance. The test is unchanged from gate 6.4 — *a distinct outcome is outside this phase* — and the deviation stop puts the appended text next to the phase goal for the human to see.

## Chat output

`_mano/rules/implement.md` → **Implementation Output Discipline** applies in full. Build's own shape:

**Mid-run stop (budget spent):** one line naming what is left, from the ledger — `[mano build]: [PHASE_ID] — S1, S2 done. 4/7 exit criteria met. Next: S3. Start a fresh session to continue.` No recap, no file list, no "AC met" checklist, no narrative.

**Terminal:** one aggregate line: `[mano build]: [PHASE_ID] built — all scope rows done, all exit criteria met in [PHASE_DIR]/progress.md. Run mano review to close the phase.`

**Deviation stop:** the named condition, the deviating text, and the question — nothing else. Then stop; do not continue into code while the question is open.

Two suffixes are permitted, and only when one genuinely applies: a short note about a non-acceptance deviation that did not weaken verification, and a project-relevant decision worth preserving, offered for capture in the artifact that owns it. An unmet Exit Criterion is never a permitted suffix — gate 10.1 leaves the row open instead.

When `mano build` is the terminal action of an armed `mano mode auto` chain, the aggregate or deviation line is the build action's log, followed by the required `[mano auto]` closing block from `_mano/workflow.md`. That block is the only permitted content after the line.

## Forbidden

- Do not write, read, or create story files. Stories belong to the other path; a phase holding both ledgers is refused.
- Do not hand-write, hand-edit, or reformat `progress.md`. Every change goes through `progress.js`.
- Do not paraphrase, shorten, or "tidy" a row's text — not at `init` (the parser owns it), not in a correction (the user owns it).
- Do not pre-decompose scope rows into sub-rows before building them.
- Do not accept a free-text argument as scope.
- Do not run `mano review`, close the phase, or scope another phase. Built is not closed.
- Do not edit the phase brief or any other input artifact — flag and route instead.
