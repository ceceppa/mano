---
name: mano-task
description: Use to implement one narrow piece of work directly, without a phase. Takes an existing backlog item's title or a plain description of new work, makes sure the item is clearly written first, then implements exactly that item. Refused while a phase is open.
requires: []
---

# `mano task "[item title or what you want]"` — implement one item without a phase

## Language check — before any response

After loading this contract and its required rules, run `node _mano/scripts/settings.js language` from the project root **before the first user-facing message or any project write**. Use the returned `language.chat` for all conversation, including progress, questions, errors, and the final response; use `language.artefacts` for new planning artifacts and `language.build` for new implementation content (code, tests, product documentation, and product/UI text, including preview copy). The command resolves missing or `null` `artefacts` through `build`, then `chat`, then `null`. Never read settings JSON directly or infer languages from the prompt, source files, or this skill's English examples. A `null` value preserves existing behaviour for that channel only. If the command fails or any of the three fields is absent, report the failure and stop; do not guess.

This check applies on direct invocation, auto-chain handoff, and resumption after interruption or compaction. Re-run after an owner or language change. English response examples, including “exact” or one-line templates, constrain structure and meaning, not prose language: translate their prose into `language.chat`. Preserve command names, paths, required labels, status tokens, and verbatim quotations or diagnostics. Before sending **each** message, check its prose against `language.chat`; before each project write, check planning prose against `language.artefacts` and implementation content against `language.build`. Do not emit an extra language-confirmation message. The human's own words stay verbatim in whatever language they used.

## What it is for

`mano task` is for validating a single narrow idea: build one piece, try it for real, then decide the next one. It skips the phase brief, stories, ledger, and review. It keeps everything that makes the result trustworthy: the item is written down before any code, the artifacts are followed, missing decisions are routed to their owners, and the item only closes on evidence.

A phase is the right tool when several items have to land together, or when the work needs a goal and a review. `mano task` is the right tool when one item can be built and judged on its own.

This file is the complete contract. It carries its own copies of the `mano dev` / `mano build` readiness and done gates, adapted from a story to a backlog item; each copy is marked with the `_mano/rules/implement.md` step it mirrors, so a change to one is easy to carry to the other. Do not load `_mano/rules/implement.md` as well: its phase-scope gate assumes a phase brief, and here there isn't one.

`mano task` is only ever started by the human. Auto mode never chains into it, `mano continue` never selects it, and no other skill's `Next:` line offers it as a substitute for a phase. Once the human has typed it, auto mode may run the owner of a readiness gap and come back to the item (see **Auto mode: gap repair**).

## Steps

1. **Check the gate.** Run `node _mano/scripts/state.js --task`. On `TASK: refused`, stop: a phase is open, and its own path owns the code until review closes it. Relay `OPEN_PHASE` and `REASON` in the refused output (see Output) and write nothing. Closing a `needs-human` item is the one exception: it changes a status line, never code, so it runs whatever the gate says. The `NEEDS_HUMAN:` lines list every item waiting on the human. The `IN_TASK:` lines list every item an earlier run edited and didn't finish; if one is not the item this request names, carry it to the human as one `⚠ Verify:` line (`"<title>" is still in-task from an earlier run`) and continue.
2. **Find the item.** Run `node _mano/scripts/state.js --titles --match "<text>"`, with the request itself when it reads like a title, otherwise its most distinctive word. Never open `backlog.md` to search it.
   - **One exact title match** (case-insensitive) → that item. Go by its status: `backlog` → step 3. `in-task` → an earlier run started it and didn't finish: skip step 3, since the item was written before that run's first edit, and go to step 4, treating the changes it left as this item's work so far. `needs-human` → **Closing a `needs-human` item** below. `in-phase-*` → stop; it belongs to its phase (`mano dev` / `mano build`). `resolved` or `rejected` → stop and say so; a change to finished work is a new item, so offer to run the request as one.
   - **A gap type** (`spec-gap`, `rule-gap`, `ux-gap`, `ui-gap`) is a decision, not code: stop and route it to `mano spec` / `rules` / `ux` / `ui`.
   - **No exact match** → the request is new work. If the roster shows titles that look like the same work, list them and ask once whether it is one of those or a new item. Otherwise go to step 3 with a new item.
3. **Clarify the item** (see **Clarify before code**). This step ends either with a clearly written item in `backlog.md` and its outcome, or with questions for the human and no other writes.
4. **Read project context before you change anything:** the item's context, the artifacts it names, and `_mano_output/project-rules.md` for the area you'll touch. Then read source.
5. **Run the readiness gates (R2–R5) and the escalation check.** If any of them stops you, stop before you edit anything. In auto mode, check **Auto mode: gap repair** before handing back.
6. **Mark the item `in-task`, then implement exactly this item** (see Rules). Before the first edit, run `node _mano/scripts/backlog.js task-status --title "<title>" --to in-task`; skip it only when the item is already `in-task`. The script refuses to move a `backlog` item anywhere else, so step 8 can't run without it.
7. **Verify.** Run every build, lint, type-check, and test command through `node _mano/scripts/verify.js -- <command>`. If a failure's fix is inside this item's scope, fix it and re-run. Otherwise stop, report the failure, and leave the status alone.
8. **Run the done gates (D1–D2), then write the status** with `node _mano/scripts/backlog.js task-status`. Never edit a status or `Check:` line by hand.
   - Both gates pass → `--title "<title>" --to resolved`.
   - D1's only shortfall is a human-only part (see D1) → `--title "<title>" --to needs-human --check "<what the human should try, one line>"`.
   - Anything else → no status write; the item stays `in-task` and is reported as partial.
9. **Report** (see Output).

## Clarify before code

An item is clearly written when its outcome can be checked: what a user, test, or caller can see happen once it's done. A backlog item has no acceptance criteria, so this outcome stands in for them, and the done gates check against it.

**R1 — Write the outcome.** In one or two lines, write the observable outcome. Every part of it must come from the item's context, an artifact it names, or the human's words in this conversation, never from what you'd expect such a feature to do.

**For new work, draft the item first.** Title: short and specific. Type: `feature`, `bug`, `refinement`, `tech-debt`, or `test`, never a gap type. Context: at most 5 lines, built from the human's words; keep their phrasing where you can and add nothing they didn't say.

**Ask before writing when the outcome can't be grounded.** Ask the human when:

- a part of the outcome would be your guess: "make it feel better", "improve the inventory";
- the item names an open detail itself ("Open product detail: …", "TBD", a question);
- it uses a noun the item and artifacts never define ("the active ball", "the default view");
- it gives a short list that may be only examples, and the full set changes what gets built;
- it describes something that starts but never says what ends it or what happens at the edge: when the effect stops, what reverts, what happens on the floor, at zero, or when two happen at once.

Ask all your questions at once, numbered, one decision each, and only those whose answer changes what gets built. Ask *what* it does, never *how* it's built. These are not yours to ask:

- the stack, a library, storage, or architecture → `mano spec`;
- a number, duration, radius, or other default → R2 routes it to `mano spec`;
- how a player picks between options → R3 routes it to `mano ux`;
- anything the item already states. Don't re-open it.

When the item is already clear, ask nothing: no confirmation round and no "does this look right?".

❌ "Should the colour change use a shader or a material swap?" (how, belongs to `mano spec`)
❌ "Which shade of red?" (a value, belongs to `mano spec` via R2)
✅ "Does the ball stay coloured while it holds something, or flash once when the capture happens?"

**Write the item.** Once the outcome is grounded, which may be right away or after the human answers:

- new item → `node _mano/scripts/backlog.js add --title "<title>" --type <type> --source "mano task" --context "<context>"`. If it prints `SIMILAR`, carry that to the human as one `⚠ Verify:` line and continue.
- existing item whose context was missing what the answers supplied → `node _mano/scripts/backlog.js update --title "<title>" --context "<context>"`, keeping every existing line that still holds and adding the answers in the human's words.

Then continue to step 4 in the same turn. The human's answers are the approval, so there is no second confirmation. Never write the item and then stop to ask whether to implement it.

**Too big for one item** → don't clarify, escalate (see below). Questions are there to pin down one item, not to break a feature into many.

## Readiness gates — before any edit

A stop here means **no edits**: no source, no tests, no artifacts. The item keeps its status: `backlog`, or `in-task` when an earlier run started it. A new item added in step 3 stays in the backlog, which is where it should be. Name the gate, quote what's missing, and name the owning command with what it has to decide after the item title. An owner handed only a title has nothing to write. Do not write the gap into `backlog.md` yourself; the human decides whether to record it.

<!-- mirrors _mano/rules/implement.md 6.2 -->
**R2 — Spec-owned default gap.** If the item needs a starting state, first-use state, capacity, radius/range, count, duration, threshold, spawn amount, or other behaviour-driving default, a canonical spec section must state the owning field/config/constant and its exact value or relationship. A vague phrase such as "small area" is not an implementation value. If it's missing, stop → `mano spec "[the item title]: [each missing value, named]"`. `mano spec` writes a directive like that into `tech-spec.md` with no phase and no backlog row. Do not choose a default yourself, add a temporary literal, or treat a test fixture as the product default.

<!-- mirrors _mano/rules/implement.md 6.3 -->
**R3 — Player-choice UX gap.** If the item lets a player choose among two or more simultaneously available tools, buildables, abilities, modes, rewards, or alternatives, `_mano_output/ux-flow.md` must define how the player invokes the choice, selects/changes the active option, sees that active state, and receives locked/unavailable/cancel feedback. If it doesn't, or the file doesn't exist, stop → `mano ux "[the item title]: [the choice that needs a flow]"`. Do not invent a hotkey, picker, cycling scheme, default active item, or HUD treatment.

<!-- mirrors _mano/rules/implement.md 7–9 -->
**R4 — Tech-spec pre-read.** If the item is setup, tooling, infrastructure, or dependency work, or involves user-entered or local data, read `_mano_output/tech-spec.md` first.
- Library choices, the package manager, and install commands there are normative. Run install commands exactly as written; don't merge, reorder, or switch tools.
- Never run a project generator against the project root, and never move, rename, or delete existing files to make room for one. If the item needs one and the tech spec has no guarded `node _mano/scripts/scaffold.js run ...` command for it, stop → `mano spec "[the item title]: scaffold command"`.
- If the tech spec says the data persists across restarts, restart persistence is part of R1's outcome, not an extra.
- If the item needs a stack decision the tech spec doesn't make (a new library, storage, or service), stop: escalate (see below).

**R5 — Contract contradiction.** If the R1 outcome needs the opposite of what `ux-flow.md`, `design-brief.md`, or a value in `tech-spec.md` states, stop. Both are the human's decisions, so which one stands is theirs to say: quote both and raise one `❓ Decide:`. The route writes the item's version into the owner's artifact as a replacement: `mano ui "<item title>: <the item's version, in its words> (replaces: <the artifact's statement>)"`, or `mano ux` / `mano spec` for their files. Running it is the answer. Build against neither version until the artifact agrees with the item. Any other contradiction with `tech-spec.md`, or one with `project-rules.md`, is an escalation (below).

❌ `Next: mano ui "Visible shield glow"` (a title gives the owner nothing to write)
✅ `Next: mano ui "Visible shield glow: the glow stays on for the whole immunity window (replaces: the shield shows only on a blocked hit)"`

## Escalate instead of implementing when

- the task requires a significant architecture decision
- requirements stay materially ambiguous after clarification
- implementation would affect multiple major systems
- the task conflicts with existing project rules
- completing it requires substantial work outside the backlog item

In those cases make no edits and leave the status as it is. Name the trigger in one line, then recommend creating a phase: `mano start` with this item.

## Auto mode: gap repair

When `state.js --task` reports `MODE: auto`, a readiness stop that routes to `mano spec`, `mano ux`, or `mano ui` doesn't wait for the human to type the route. Typing `mano task "<item>"` approved this one item, and auto mode runs the commands the human would otherwise type next: the owner's command, then this task again. It removes typing, not decisions.

**All of these must hold:**

- `state.js --task` reported `MODE: auto` in this run, and nothing is pending: no unanswered clarify question, no script failure, no stop from the human.
- The stop is R2, R3, or R4's missing scaffold command, or R5 once the human has answered its `❓ Decide:` in favour of the item. R5 always pauses for that answer first; an answer for the artifact ends the run with the item untouched. An escalation (R4's stack decision included), a gap-type item, a done gate, and a failing check never chain. Their next step is `mano start`, a decision, or a fix, and those belong to the human.
- The item is written in `backlog.md` with its R1 outcome. The owner supplies a value, a flow, or a treatment, never the outcome.
- This run hasn't already run that owner. One attempt per owner per run.

**If eligible, in this same turn:**

1. Print the stop's `Why:` line and the owner command you're inserting as this action's log, with no `Next:` block. The item keeps its status: nothing has been edited, so don't mark it `in-task`.
2. Run exactly the command the manual `Next:` would have printed (`mano spec "<item title>: <each missing value, named>"`, `mano ux "<item title>: <the choice that needs a flow>"`, or R5's replacement), loading that skill's own contract and required rules. It keeps its own questions, `❓ Decide:` lines, and hook triage. The ban on editing `tech-spec.md`, `ux-flow.md`, and `design-brief.md` binds `mano task`, not the owner.
3. Once the owner and its hook triage finish, re-run `node _mano/scripts/state.js --task`. If `MODE` is now `manual`, or the human said stop, hand back with `Next: mano task "<item title>"`. Otherwise resume this item at step 4: reread what the owner changed, then run R2–R5 in full again before any edit.

**Pause instead** when the owner asks a question or raises `❓ Decide:`, routes the request somewhere else instead of writing it, or fails, and when the rerun gates stop again on an owner this run already ran. Print the chain's closing block (see Output) and wait. The human's answer resumes the chain in the same turn.

Nothing else chains. A finished task never chains into another one, and the chain never runs `mano start` or closes a `needs-human` item. Picking what to build next is the human's call.

A task chain keeps no `chain.js` record, because a task has no phase. The item in `backlog.md` is its durable state: if a session reset cuts the chain, `mano task "<item title>"` picks it up, and whatever the owner already wrote stays in its artifact.

## Rules

- Implement exactly one backlog item, and only after it is written in `backlog.md`.
- Read existing project context before implementation.
- Do not create a phase brief, stories, or a `progress.md` ledger.
- Do not edit `tech-spec.md`, `project-rules.md`, `ux-flow.md`, or `design-brief.md`. A missing or wrong decision there goes to its owning command, as the gates say.
- Do not expand the scope of the backlog item.
- Do not implement adjacent backlog items, even when they touch the same code.
- Do not introduce new architecture unless the item requires it.
- Do not add dependencies unless the item requires them.
- Follow existing architecture and project rules.
- Run relevant tests/checks.
- Report anything discovered that belongs in another backlog item. Report it only. Do not add it to `backlog.md` unless the user approves; once they do, use `node _mano/scripts/backlog.js add`.

## Done gates — before the status may change

A failure here leaves the status `in-task` and is reported. Keep the edits, and say they're partial.

<!-- mirrors _mano/rules/implement.md 10.1 -->
**D1 — Outcome evidence.** Reread the outcome you wrote for R1. For every part of it, point to concrete evidence from this turn (a test that exercises it, or a manual/runtime check you ran) showing the outcome happens through the route the item describes. A green suite is not enough if nothing in it exercises the outcome. Any assertion, fixture, comment, skipped test, or observed result that says the opposite (success expected as failure, available expected as unavailable) proves the item is **not done**, even if everything passes. If current code or an artifact deliberately keeps the opposite behaviour, stop and report the contradiction; do not invert the test or reword the outcome to match. If a visual or experiential part can't be checked, don't resolve: when every other part has evidence, the item becomes `needs-human`.

**`needs-human` is a handoff, not an escape hatch.** Use it only when every part of the outcome you *can* exercise has evidence from this turn, and what's left is inherently visual, experiential, or otherwise impossible for you to check honestly (how it looks, how it feels, a device you don't have). It is never for a missing test you could have written, a tool you didn't try, a failed check, or a contradiction. Those leave the status `in-task` and report the item as partial. The `Check:` line names one thing the human does and what they should see.

<!-- mirrors _mano/rules/implement.md 10.2 -->
**D2 — Design-contract conformance.** If the item produced or changed a user-visible surface and `_mano_output/design-brief.md` names components for that surface, confirm from **this turn's edits** that the surface uses each named one: its name, or the file that defines it, appears in what you wrote. A shared theme, matching colour, copied style, or hand-built lookalike is not the component. A missing one means not done.

## Closing a `needs-human` item

The human answers the `Check:` line, either by replying in this conversation or by running `mano task "<title>"` again later. Don't re-implement and don't re-run the gates. Every write goes through `backlog.js task-status`, which refuses any other move.

- **No answer yet** (a bare re-run): print the item's `Check:` line and ask once: works, broken, or do you want it different?
- **Works** → `--to resolved`. The `Check:` line stays on the item as the record of how it was verified.
- **Broken: \<what\>** → `--to backlog --failed "<their words, verbatim>"`.
- **Works, but I want it different: \<what\>** → `--to backlog --redirect "<their words, verbatim>"`. This is a new outcome, not a fix, so the next run clarifies it again before any code.
- **Didn't check** → no write; it stays `needs-human`.

After `broken` or a redirect, hand back with `Next: mano task "<title>"`. The next run starts from the human's words now in the item's context.

## Output

```
[mano task]: <item title> → resolved
Outcome: <the R1 outcome, one line>
Changed: <files>
Checks: <verify.js PASS lines>
Discovered (not added): <one line each, or "none">
```

Add `Added: <title> (new backlog item)` or `Updated: <title> (context)` under the first line when step 3 wrote the item.

When the item needs clarification (nothing written):

```
[mano task]: <item title or "new item"> — needs clarification
Outcome so far: <the parts already grounded, one line>
1. <question>
2. <question>
```

When the gate refuses (nothing written):

```
[mano task]: refused — <OPEN_PHASE> is open
Why: <REASON, one line>
Next: <the command REASON names for that phase>
```

When a readiness gate stops or escalation fires (no edits made):

```
[mano task]: <item title> — not implemented
Why: <R2/R3/R4/R5 or escalation trigger> — <what's missing, or both statements for R5, one line>
❓ Decide: <R5 only: keep the artifact's version, or replace it with the item's?>
Next: <mano start | mano spec "<item>: <what's missing>" | mano ux "<item>: <what's missing>" | R5: mano <ux|ui|spec> "<item>: <item's version> (replaces: <statement>)">
```

When the only gap is a human-only check (D1, `needs-human`):

```
[mano task]: <item title> → needs-human
Outcome: <the R1 outcome, one line>
Changed: <files>
Checks: <verify.js PASS lines>
Check: <what to try, one line> — reply "works", what's broken, or how you want it different
```

When a done gate or verification fails (edits kept, status unchanged):

```
[mano task]: <item title> — partial, still in-task
Why: <D1/D2 or failing check> — <one line>
Changed: <files>
Next: mano task "<item title>" to finish it
```

When an auto-mode run inserted an owner (see **Auto mode: gap repair**), add one closing block after the last action's own log. A run that inserted none ends at its own block.

```
[mano auto]: task "<item title>" — <first action> → … → <last action>
- Ran: <actions, in order>
- Stopped: <resolved | needs-human, check above | partial, still in-task | waiting on the question above | <gate>, not repairable>
- Remaining: task "<item title>" — omit when none
⚠ Verify: <every advisory flag collected across the run, one per line — omit if none>

Next: <the final block's Next:, or reply to the question above — the task resumes automatically>
```
