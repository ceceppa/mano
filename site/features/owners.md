# Team owners

```
mano owner alice
```

Two people, one repo, independent phases.

By default a phase is `_mano_output/phase-7/`. In a team that collides immediately — two people both scoping "phase 7".

With an owner set, phase-scoped commands use `_mano_output/alice-phase-1/` and `in-alice-phase-1` backlog statuses, on Alice's own number sequence. Bob's `mano owner bob` runs an independent sequence in the same repo.

## Where the slug lives

The slug lives in repository-local git config (`mano.owner`), isn't committed, and `MANO_OWNER` overrides it per shell — so linked worktrees can differ.

In chat:

```
mano owner           # what this clone is set to
mano owner bob       # set it
mano owner clear     # back to unowned `phase-N/` routing
```

From a terminal, if you'd rather not go through the agent:

```bash
git config --local mano.owner       # read it
export MANO_OWNER=bob               # override, for agents launched from this shell
```

`MANO_OWNER` wins over git config, so a linked worktree — or a second agent started with a different environment — can run under a different owner than the checkout beside it.

A slug is a lowercase identifier — letters, digits and hyphens, up to 48 characters (`alice`, `gameplay-team`). It becomes a folder name and a backlog status, so it has to survive both.

::: warning What this is not
Ownership selects *work*, not *isolation*. You still use branches and worktrees for merge isolation, and you still coordinate changes to the shared backlog, spec, and rules files. Mano namespaces identity; git handles execution.
:::

## Clearing it

```
mano owner clear
```

Routing returns to unowned `_mano_output/phase-N/` folders and `in-phase-N` statuses. A phase already created under a slug keeps it — `mano owner` configures routing, it never renames or migrates a phase.
