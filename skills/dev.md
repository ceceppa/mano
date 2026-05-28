---
name: dev
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

- **No implementable story → stop.** If every story is already `done`, or the requested story does not exist, output one line stating the phase is complete and that `mano review` or `mano start` is the user's call. Do not start, scope, or plan a new phase. Do not run `mano start` or `mano stories`.
- **Respect order.** If an earlier story is still `pending`, stop and tell the user which story would be skipped. Do not bypass without explicit confirmation.
- **AC only.** Implement the story's acceptance criteria — nothing beyond them. On a genuine gap, stop and name the Mano flow that owns the decision; do not invent behaviour.
- **One-line done.** After implementing, the entire chat response is `Story [N] done — status updated in stories/README.md`. No recap, no checklist, no AC restatement. The only permitted addition is a real deviation.

If this file and `AGENTS.md` ever disagree, `AGENTS.md` wins — fix this pointer.
