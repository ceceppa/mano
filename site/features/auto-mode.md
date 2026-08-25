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
- It stops at any open question or missing artifact.
- "stop" or "wait" ends it immediately.

The chain ends at [`mano build`](/features/build) — but that pairing is a convenience, not a coupling. Build is one of the two ways into code and you can type it yourself in `manual` mode any time a phase doesn't need story files.

## Back to manual

```
mano mode manual
```

## Where the mode lives

The mode lives in repository-local git config (`mano.mode`), isn't committed, and `MANO_MODE` overrides it per shell — so linked worktrees can differ.

In chat:

```
mano mode           # what this clone is set to
mano mode auto      # set it
mano mode clear     # back to the default, manual
```

From a terminal:

```bash
git config --local mano.mode      # read it
export MANO_MODE=manual           # override, for agents launched from this shell
```

It isn't committed on purpose: the mode records **how much you review**, which is a property of you and this clone, not of the project. A teammate cloning the repo starts in `manual`.

Every state projection prints the active mode as `MODE:`, so a skill reads it there rather than asking you.

## When to use it

Once you've read enough briefs to trust their shape. Until then, typing each command is what keeps you reading the artifacts — which is where Mano's value actually is.
