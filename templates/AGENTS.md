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
3. Before implementing the requested story, check whether any earlier story in the index is still `pending`. Treat numbered stories and lettered insertions as ordered work unless the README or story notes explicitly say otherwise.
4. If an earlier story is still `pending`, stop and tell the user which story would be skipped. Do not implement the later story unless the user explicitly confirms they want to bypass the suggested order.
5. Read the story file first. Treat it as the primary implementation contract. The Implementation Reference section should carry the applicable rules plus any required files, modules, contracts, constraints, ownership boundaries, and prohibitions for that story. Treat exact prop names, attribute names, variant names, state keys, ownership statements, file paths, dependency names, and install commands written there as normative.
6. If the story is bootstrap, setup, tooling, infrastructure, or dependency-related, also read `_mano_output/tech-spec.md` before implementing. Treat library choices, package-manager choice, and install commands there as normative unless the story file already repeats them exactly.
7. If the story involves user-entered state, forms, onboarding drafts, settings, or other local data, check whether the story or tech spec says that data should persist across app restarts. If it should, treat restart persistence as part of the required behaviour, not as an optional enhancement.
8. Read `_mano_output/project-rules.md` only when the story explicitly points to a rule there or something is still ambiguous after reading the story and any mandatory tech-spec pre-read.
9. After implementing, update the story's status to `done` in the stories README.md.

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
