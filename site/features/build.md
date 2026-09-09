# Build mode

```
mano build
```

One of the **two ways into code**. A phase uses one or the other, never both.

- **`mano stories` → `mano dev`** decomposes the phase into story files, then implements them one at a time. Suits a large phase, and keeps planning and implementation on separate models if you want that.
- **`mano build`** works straight from the brief's numbered `## Phase Scope` items — the ones you already approved — with no invented decomposition. Suits a phase small enough to hold in one contract.

A phase holding both ledgers is refused. Pick one and delete the other.

## Nothing is decomposed, so nothing can drift

Because build takes the numbered scope items verbatim, there is no intermediate artifact to disagree with the brief. What you approved is what gets built.

Progress is tracked in a ledger on disk — `_mano_output/phase-N/progress.md`:

```markdown
| #   | What                              | Status  |
|-----|-----------------------------------|---------|
| S1a | Demo selector                     | done    |
| S1b | Consistent scaling across demos   | pending |

| #   | Criterion                                          | Status |
|-----|----------------------------------------------------|--------|
| E1a | Open the playground: a 2D/3D selector is visible    | met    |
| E2a | Any demo on a high-DPI display renders consistently | pending |
```

## Built is not proven

Two status vocabularies, and the writer enforces the difference: scope rows are `pending | doing | done`, criteria are `pending | met | needs-human`.

A criterion that is inherently visual gets handed to you as `needs-human` with a reason, rather than claimed. A phase does not close on rows that merely say the code was written.

## Correcting a running build

Report a defect while build is running and the correction is recorded as a durable event in the ledger before anything is reopened — so a run that dies mid-fix routes the next `mano build` straight back to it, and sign-off refuses to close the phase while it's open.

```
mano build "the selector doesn't survive a reload"
```

A clear correction inside the phase goal is recorded, implemented, and verified in the same run, without asking you to approve it again. This also applies when the correction needs a new scope row linked to an existing exit criterion. If the request is ambiguous, conflicts with an existing contract, or needs a new exit criterion, build asks for the missing decision, then continues once you answer. A distinct new outcome belongs in the backlog or a later phase.

Your words go into the ledger, not just the conversation. A conversation doesn't survive a compaction, a restart, or an interleaved command.

## When to use it

Whenever the phase is small enough to hold in one contract — with or without [auto mode](/features/auto-mode).
