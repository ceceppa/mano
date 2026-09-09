# Team owners

```
mano owner alice
```

Two people, one repo, independent phases.

By default a phase is `_mano_output/phase-7/`. In a team that collides immediately — two people both scoping "phase 7".

With an owner set, phase-scoped commands use `_mano_output/alice-phase-1/` and `in-alice-phase-1` backlog statuses, on Alice's own number sequence. Bob's `mano owner bob` runs an independent sequence in the same repo.

## Where the slug lives

Mode, track, remaining approved actions, skips, and repair attempts live in committed `_mano_output/[owner].json` files. Without an owner, they use `_mano_output/.default.json`. Only the selected owner stays in ignored `_mano_output/.local.json`. Environment variables override the stored values for a shell or worktree. See [Owner JSON files](/features/#owner-json-files) for the file structure, commands, and steps to resume on another computer.

In chat:

```
mano owner           # what this clone is set to
mano owner bob       # set it
mano owner clear     # back to unowned `phase-N/` routing
```

From a terminal, if you'd rather not go through the agent:

```bash
node _mano/scripts/owner.js show   # read it
export MANO_OWNER=bob               # override, for agents launched from this shell
```

`MANO_OWNER` wins over the local selection, so a linked worktree — or a second agent started with a different environment — can run under a different owner than the checkout beside it.

A slug is a lowercase identifier — letters, digits and hyphens, up to 48 characters (`alice`, `gameplay-team`). It becomes a folder name and a backlog status, so it has to survive both.

::: warning What this is not
Ownership selects *work*, not *isolation*. You still use branches and worktrees for merge isolation, and you still coordinate changes to the shared backlog, spec, and rules files. Mano namespaces identity; git handles execution.
:::

## Clearing it

```
mano owner clear
```

Routing returns to unowned `_mano_output/phase-N/` folders and `in-phase-N` statuses. A phase already created under a slug keeps it — `mano owner` configures routing, it never renames or migrates a phase.

To resume elsewhere, commit and pull `_mano_output/alice.json` with the phase artifacts and code. Run `mano owner alice` once on the other computer, then `mano continue`. The ignored `.local.json` selects an owner independently in each checkout. Settings from older Mano versions migrate automatically when corresponding JSON state is missing; existing JSON values win.
