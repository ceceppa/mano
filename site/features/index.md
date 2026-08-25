# Features

The loop — `start → spec → rules → stories → dev → review` — is the default and covers most phases. These are the parts you reach for when a project grows past it.

| | What it is | When you need it |
| --- | --- | --- |
| [Build mode](/features/build) | Implement a phase straight from its approved brief, no story files | The phase is small enough to hold in one contract |
| [Auto mode](/features/auto-mode) | Chain the commands you'd otherwise type, armed only by your scope approval | You've read enough briefs to trust their shape |
| [Import](/features/import) | Turn an existing PRD or document into a backlog, then stop | You already wrote the requirements somewhere else |
| [Team owners](/features/owners) | Namespace phases per person, so two people don't both scope "phase 7" | More than one person planning in one repo |
| [Tracks & filters](/features/tracks) | Narrow what a phase is allowed to contain | The backlog has absorbed several documents |
| [Hooks](/features/hooks) | Wire your own review checklist into any skill | You've made the same correction three phases running |

Everything here is optional. Nothing is on by default, and nothing arms itself.

## Local settings

Three of them are settings rather than actions, and all three live the same way: in **repository-local git config**, uncommitted, overridable per shell.

| Command | Git config key | Shell override | Default |
| --- | --- | --- | --- |
| [`mano owner`](/features/owners) | `mano.owner` | `MANO_OWNER` | unset — `phase-N/` routing |
| [`mano mode`](/features/auto-mode) | `mano.mode` | `MANO_MODE` | `manual` |
| [`mano track`](/features/tracks) | `mano.track` | `MANO_TRACK` | unset — untracked planning |

None of them write a planning artifact, and none of them travel with the repo: a teammate who clones it gets the defaults until they set their own. Each has a `show` (the bare command) and a `clear`.

Because the value is per-clone and the `MANO_*` variable wins over git config, a linked worktree — or a second agent launched from a different shell — can run under a different owner, mode, or track than the checkout beside it.
