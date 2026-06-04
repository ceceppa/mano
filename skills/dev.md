---
name: mano-dev
description: Use to implement the next pending story for the active phase. Thin entry point — the implementation contract lives in AGENTS.md, not here.
---

# mano dev — implement the next pending story

This skill is a **pointer**, not a contract. The implementation contract is `AGENTS.md` → **"Implementing a story"** and **"Implementation Output Discipline"**. Read those and follow them exactly. Do not re-derive or paraphrase them from this file.

`mano dev` is the sanctioned path from a finished `stories/` folder into code. It runs on the implementing agent (the small-context coding model), so this file stays deliberately short.

## What to do

1. Read `AGENTS.md` → "Implementing a story" and follow it step by step.
2. Implement only the selected story's acceptance criteria.
3. Mark the story `done` in the stories README index.

## Hard stops (from AGENTS.md — repeated here only so they are never skipped)

- **No implementable story → stop — but only when *every* row is `done`.** The `Status` column is the only signal. A story is implementable if and only if its Status is not `done`; its number, letter, or title grants no exemption. There is no "refinement"/"extra"/"optional"/"addendum" class a user must separately request — if a row is in the index and not `done`, implement it. A lettered story (`4a`, `4b`) is its own pending work, **not** a sub-part of done story `4` that inherits its done-ness; letters/numbers are ordering only. "The core/main stories are done" is not a stop condition. Before claiming the phase is done, count rows whose Status is not `done` — if greater than zero, implement the next pending story; do not announce completion. Only when every row is `done` (or the requested story does not exist): output one line — the phase's stories are all done but the phase is **not closed** until `mano review` runs (review is mandatory, not optional); direct the user to `mano review`. Do not call the phase "complete" (a phase is complete only once review moves its backlog items off `in-phase-[N]`), and do not present `mano start` as an equal option — `mano start` will refuse to scope the next phase until review closes this one. Do not start, scope, or plan a new phase. Do not run `mano start` or `mano stories`.
- **Respect order.** If an earlier story is still `pending`, stop and tell the user which story would be skipped. Do not bypass without explicit confirmation.
- **AC only.** Implement the story's acceptance criteria — nothing beyond them. On a genuine gap, stop and name the Mano flow that owns the decision; do not invent behaviour.
- **`Not this story` is a hard no.** Treat every item in the story's `Not this story` / out-of-scope section as a prohibition equal to a `Do not:` line — implement none of it, even when the chosen node/type/component or a library default makes that behaviour the "natural" thing to add (e.g. an animated-sprite type showing a *static* frame: the type does not authorise the animation the story excludes). If you think an excluded item is required for the AC to work, that's a gap — stop and surface it; do not add it on your own initiative.
- **One-line done.** After implementing, the entire chat response is `Story [N] done — status updated in stories/README.md`. No recap, no checklist, no AC restatement. The only permitted additions are a real deviation or a project-relevant decision worth preserving (offered for capture) — per `AGENTS.md` step 12 and "Implementation Output Discipline". Nothing else.

If this file and `AGENTS.md` ever disagree, `AGENTS.md` wins — fix this pointer.
