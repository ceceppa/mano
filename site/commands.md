---
title: "Command reference"
description: "Find every Mano chat command for planning, implementation, and review, with guidance on artifact ownership, build paths, and workflow modifiers."
---

# Commands

Type these in your AI IDE's chat, not a terminal. Mano is a set of skills your agent reads — there is no `mano` binary.

## The full list

| Command | What it does |
| --- | --- |
| `mano` | Show available commands and current status. |
| `mano status` | Read project state and show where you are and what to do next. |
| `mano help [skill]` | Show what a skill does and when to use it. |
| [`mano import [doc]`](/features/import) | Turn an existing PRD or document into a backlog, then stop. |
| `mano start` | Scope a new project or phase. Writes nothing until you approve. |
| `mano continue` | Run the next logical action, if it's unambiguous. |
| `mano spec` | Technical decisions, contracts, data models. |
| `mano rules` | Conventions: folder structure, naming, patterns. |
| `mano ux` | User flows. |
| `mano ui` | Visual design direction. |
| `mano stories` | Decompose the phase into self-contained stories. |
| `mano dev` | Implement the next pending story. |
| [`mano build ["<fix>"]`](/features/build) | Build the phase straight from its brief, no story files. |
| `mano review` | Record outcomes, triage feedback, close the phase. |
| [`mano owner [slug]`](/features/owners) | Set this clone's phase owner, for parallel work. |
| [`mano mode [auto\|manual]`](/features/auto-mode) | Whether finished actions chain automatically. |
| [`mano track [name]`](/features/tracks) | Set an optional experiment or work track. |

## What each action owns

Every artifact has exactly one owning command. This is the rule that keeps a value from drifting between two files that both half-describe it.

| Artifact | Owned by | Holds |
| --- | --- | --- |
| `backlog.md` | `mano import`, `mano review` | Everything not being built now |
| `phase-N/phase-brief.md` | `mano start` | Goal, scope, what's excluded, exit criteria |
| `tech-spec.md` | `mano spec` | Decisions and why — never file paths |
| `project-rules.md` | `mano rules` | Conventions and file placement |
| `ux-flow.md` | `mano ux` | Flows and states |
| `design-brief.md` | `mano ui` | Visual direction |
| `phase-N/stories/` | `mano stories` | Self-contained units of work |
| `phase-N/progress.md` | `mano build` | Scope and exit-criteria ledger |
| `reviews.md` | `mano review` | What held, what didn't |

### The three that own no artifact

Mode, track, remaining approved actions, skips, and repair attempts live in committed `_mano_output/[owner].json` files. Without an owner, they use `_mano_output/.default.json`. Only the selected owner stays in ignored `_mano_output/.local.json`. Environment variables override the stored values for a shell or worktree. [Details →](/features/#owner-json-files)

The split between spec and rules catches people out. A concrete file path in `tech-spec.md` is a leak: the spec records the *decision* ("Prisma + SQLite"), while *where things live* belongs to `project-rules.md`.

## Two ways into code

A phase uses one or the other, never both.

**`mano stories` → `mano dev`** decomposes the phase into story files, then implements them one at a time. Suits a large phase, and keeps planning and implementation on separate models if you want that.

**`mano build`** works straight from the brief's numbered scope items — the ones you already approved — with no invented decomposition. Suits a phase small enough to hold in one contract.

A phase holding both ledgers is refused. Pick one and delete the other. [More on build mode →](/features/build)

## Modifiers

`mano dev yolo` implements every currently pending story in order instead of stopping after one. It keeps every per-story gate and hard stop — it only changes how many stories one invocation covers.

In manual mode, you request it explicitly. An approved [auto-mode chain](/features/auto-mode) also uses `mano dev yolo` when the phase already has a stories index.

`mano start from source "<text>"` narrows the candidate phase items to those whose backlog `Source` matches — useful after importing several documents. `mano start from track "<name>"` does the same for a named experiment. [More on tracks & filters →](/features/tracks)

## If a command doesn't resolve

Ask your agent to read the project's `AGENTS.md` and follow the corresponding `_mano/skills/` file. Mano commands use repo-local instructions; a missing external skill does not mean Mano is unavailable. Skill names use hyphens (`mano-review`), not plugin-namespace colons (`mano:review`). See [setup and troubleshooting](/getting-started#my-agent-says-mano-isn-t-available).

---

Every optional part of Mano — build mode, auto mode, import, owners, tracks, hooks — has its own page under [Features](/features/).
