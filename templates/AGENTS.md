# AGENTS.md

This project uses **Mano** for planning. Mano is a structured thinking tool — it produces planning artifacts, not code.

## For coding agents

### Running Mano commands

If the user types a Mano command in chat, treat that as an instruction to execute the corresponding Mano planning flow yourself.

- `mano`, `mano status`, `mano continue`, and `mano help [skill]` should be handled according to [workflow.md](workflow.md).
- `mano start`, `mano spec`, `mano ux`, `mano rules`, `mano ui`, `mano stories`, and `mano review` should activate the matching skill and follow that skill's contract.
- Do not tell the user to run Mano commands manually just because they are planning commands. They are planning commands for the agent to carry out, not shell commands to bounce back to the user.

### Implementing a story

1. Find the active phase: highest numbered `phase-[N]/` folder in `_mano_output/`.
2. Check `_mano_output/phase-[N]/stories/README.md` for the story index and status.
3. Read the story file. It's self-contained — the Implementation Reference section lists which project rules apply by name.
4. If you need to look up a referenced rule, it's in `_mano_output/project-rules.md`.
5. After implementing, update the story's status to `done` in the stories README.md.

### Do not

- Modify files in `_mano/` or `_mano/templates/` — these are framework files.
- Interpret `mano` commands (e.g. `mano start`, `mano review`) as implementation instructions — these are planning commands. Execute the relevant planning flow instead.
- Create extra tracking files — Mano does not use a dedicated state file. Determine state by reading `_mano_output/` and the latest `phase-[N]/` artifacts.

## Project structure

```
_mano/                    ← Mano framework (do not modify during implementation)
├── skills/               ← Mano skill prompts
├── templates/            ← Mano templates
└── custom/               ← Optional Mano overrides and story template overrides
_mano_output/             ← Planning artifacts
├── project-rules.md      ← Rules for implementation (referenced by stories)
├── tech-spec.md          ← Technical decisions
├── ux-flow.md            ← Screen and navigation definitions
├── design-brief.md       ← Visual language
├── backlog.md            ← Future work and deferred items
├── reviews.md            ← Sprint review history (human-only)
└── phase-[N]/            ← Per-phase work
    ├── phase-brief.md    ← Phase scope and goals
    └── stories/          ← Implementation stories (start here)
```
