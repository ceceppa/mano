---
title: "Auto mode for approved development workflows"
description: "Chain Mano planning and implementation actions after approving a phase. Learn when auto mode pauses, how readiness repairs work, and how to return to manual."
---

# Auto mode

```
mano mode auto
```

Auto mode chains the commands you'd otherwise type by hand. It is armed by **one thing only** — your explicit approval of a phase scope:

```text
→ Auto mode: spec → rules → build
  Reply `1` or `go` — both approve this scope and run the chain above.
  Edit and approve together (`go, skip rules`; `1, add ux`). Pauses for
  questions; stops before review.
```

You can edit the chain in the same breath as approving it: `go, skip rules`, `1, add ux`.

## What auto mode does not do

- It never scopes a phase for you. Approval is always yours.
- It never runs `mano review`. Closing a phase is a judgement call.
- It stops at any open question. Before implementation begins, a missing or stale artifact with a clear repair route can be repaired automatically.
- "stop" or "wait" ends it immediately.

The chain ends at [`mano build`](/features/build) — but that pairing is a convenience, not a coupling. Build is one of the two ways into code and you can type it yourself in `manual` mode any time a phase doesn't need story files.

## Repairing a readiness gap

If build finds a missing or stale supporting contract before either implementation ledger exists, auto mode can run its owner (`spec`, `ux`, `ui`, or `rules`) and retry build. The approved phase must already settle the intended behavior, and the owner must not have been explicitly skipped. The revised chain and repair attempt survive a session restart.

Each owner gets one automatic repair attempt per approved run. Unresolved product choices, changes to scope, conflicts requiring a human decision, and gaps that survive that attempt still pause. The repair skill also pauses for its own questions. Build reruns full readiness before creating its ledger or writing code.

## Back to manual

```
mano mode manual
```

## Where the mode lives

Mode, track, remaining approved actions, skips, and repair attempts live in committed `_mano_output/[owner].json` files. Without an owner, they use `_mano_output/.default.json`. Only the selected owner stays in ignored `_mano_output/.local.json`. Environment variables override the stored values for a shell or worktree. See [Owner JSON files](/features/#owner-json-files) for the file structure, commands, and steps to resume on another computer.

In chat:

```
mano mode           # what this clone is set to
mano mode auto      # set it
mano mode clear     # back to the default, manual
```

From a terminal:

```bash
node _mano/scripts/mode.js show   # read it
export MANO_MODE=manual           # override, for agents launched from this shell
```

A new owner starts in `manual`. Selecting an existing owner restores their committed mode; use `MANO_MODE=manual` for a temporary override.

Every state projection prints the active mode as `MODE:`, so a skill reads it there rather than asking you.

## When to use it

Once you've read enough briefs to trust their shape. Until then, typing each command is what keeps you reading the artifacts — which is where Mano's value actually is.
