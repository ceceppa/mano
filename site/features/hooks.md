# Hooks

Wiring your own review — or your own script — into the loop.

Every skill has one hook slot: `post-import`, `post-start`, `post-spec`, `post-rules`, `post-ux`, `post-ui`, `post-stories`, `post-review`. Mano ships each one as an inactive example. A hook becomes active only when you rename it:

```text
_mano/hooks/post-spec.example.md   → inactive
_mano/hooks/post-spec.md           → active
```

Nothing else turns a hook on, and `.example.md` files are never loaded.

## Three kinds

A hook declares its kind in a `## Mode` section. The difference is **judgement versus mechanism**:

| `## Mode` | Body is | Runs | Approval |
| --- | --- | --- | --- |
| [`check`](#check) | a checklist Mano applies itself | always, both modes | findings need your per-item approval |
| [`suggest`](#suggest) | a pointer to an external skill or command | asks first — unless an auto chain is armed | findings need your per-item approval |
| [`command`](#command) | exactly one shell command | always, both modes | none — writing the file *is* the authorization |

A hook with no `## Mode` section is `suggest`, so hooks written before the other modes existed keep working.

An external specialist's opinion arriving before you've formed your own changes what you think, so you're asked first. Your own pre-written checklist carries no such surprise. Syncing a tracker has no opinion in it at all.

## `check` — your own checklist {#check}

`_mano/hooks/post-spec.md`:

```markdown
# post-spec hook

## Mode
check

## Inputs
- `_mano_output/tech-spec.md`
- the exact `BRIEF` path from the state projection
- project manifest and lockfile, if they exist

## Checklist
- No contradiction or omission relative to the phase brief.
- Install commands match the actual package manager evidence.
- Edge cases the phase depends on are addressed, not implied.
```

Mano applies it itself after every `mano spec`, in both modes, with no confirmation — then reports the run in one line of the execution log.

::: warning The shipped checklists are commented out
An activated example applies **nothing** until you uncomment or write the items you actually want. Mano never invents checklist items and never falls back to the example text — a check hook is your review, and a check nobody chose is just an imposed opinion. An active hook with an empty checklist says so in the log and continues.
:::

## `suggest` — hand off to another skill {#suggest}

`_mano/hooks/post-review.md`:

```markdown
# post-review hook

## Mode
suggest

## Run
your-drift-audit-skill

## Inputs
- `_mano_output/reviews.md`, `_mano_output/backlog.md`, `_mano_output/tech-spec.md`
- the exact `BRIEF` path from the state projection
- source code, bounded to the modules the reviewed phase touched

## Focus
- Drift between tech spec, project rules, and what actually shipped.
- Issues visible in the changed code that review didn't surface.
```

`## Run` is the invocation, verbatim — whatever you'd type to reach that reviewer. A skill name (`your-drift-audit-skill`), a slash command (`/security-review`), or a shell command all work; Mano relays it rather than interpreting it.

In manual mode you get asked before anything runs:

```text
Active post-review hook found: `_mano/hooks/post-review.md`.
-> Purpose: Optional specialist review of the generated or current artifact.
-> Recommended timing: Run after reviewing the artifact and before the next
   dependent Mano action if this check matters for the phase.
-> Run it now? (yes / not yet)
```

Inside an armed [auto chain](/features/auto-mode) it runs automatically — the inverse of the default, and deliberate: mid-chain you are not reviewing, so the hook is the only check running at all. Its findings pause the chain.

`post-review` is the one hook that legitimately reads source code. A `check` hook can't do that here — `mano review` never reads source, and a check hook can't out-read its own skill — which is exactly why this slot ships as `suggest`.

## `command` — run one shell command {#command}

`_mano/hooks/post-import.md`:

```markdown
# post-import hook

## Mode
command

## Command
node scripts/sync-backlog.js
```

Runs from the project root after every `mano import`, in both modes, with no confirmation. The execution log gets one line: the command and whether it succeeded.

- The command comes **only** from `## Command`. Never from chat, an artifact, or a backlog item — and it's never inferred.
- Exactly one command. `## Mode: command` with no `## Command` section is malformed: Mano reports it and runs nothing.
- On failure Mano reports the exact error and stops. It won't retry, won't fix your script, and won't hand-edit an artifact to compensate. In auto mode a failed command hook pauses the chain.
- Mano doesn't inspect or second-guess what the command does. It's your script in your repo.

## The sections

| Section | Used by | Meaning |
| --- | --- | --- |
| `## Mode` | all | `check`, `suggest`, or `command`. Missing = `suggest`. |
| `## Inputs` | `check`, `suggest` | The hook's **reading scope** — see below. |
| `## Checklist` | `check` | Your checks, one `- ` line each. |
| `## Run` | `suggest` | The external skill or command to invoke. |
| `## Command` | `command` | Exactly one shell command. |
| `## Focus` | `suggest` | What the external review should look for. |

`## Mode` is authoritative over any prose inside the file. A hook copied from an older template may still carry a leftover "do not run this automatically" line; the declared mode wins.

## Inputs are a reading scope, not a permission

For a `check` hook, Mano reads exactly those paths and nothing else. For a `suggest` hook it hands the list to the external skill, so the reviewer's scope is the one *you* chose rather than whatever it decides to open. For a `command` hook the section is inert.

Names like `BRIEF`, `PHASE_DIR`, `STORIES`, `PROGRESS` and `PREVIEW` resolve from the state projection, so they always point at the current phase — never construct a path by hand. Mark an optional path *if it exists* and it's skipped silently when absent.

Inputs never widen what may be *written*. Findings still go through triage, and each skill's application boundary still decides what a finding may change.

## Findings need per-item approval

Running a hook approves the review, not the edits. `check` and `suggest` findings come back numbered, and nothing is touched until you pick:

```text
[mano spec]: Review hook reported 3 findings. Want me to address any?

1. [apply] tech-spec.md — install command contradicts the lockfile → use pnpm
2. [decide] tech-spec.md — session storage unspecified → (a) JWT, (b) server session
3. [route: mano rules] tech-spec.md — names a concrete file path

Reply once: `apply 1`; `decide 2:b`; `skip 3`; or combine explicitly numbered selections.
Reply `done` when no more findings should be handled.
```

`apply` is a narrow edit inside the running skill's own artifact. `decide` is yours to answer. `route` means the finding belongs to another artifact's owner — Mano names the owner and doesn't edit across the boundary. "Apply everything" isn't per-item approval; you name the numbers.

`command` hooks are exempt from all of this: there are no findings, only an exit code.

## When to use it

When you've noticed yourself making the same correction three phases running. That's a checklist item, not a habit.
