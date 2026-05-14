# Project Instructions

This project uses **Mano** for planning. Read these files before responding to any user request:

1. `AGENTS.md` — primary contract for coding agents
2. `_mano/workflow.md` — Mano workflow and command reference
3. `_mano/skills/` — individual skill prompts

When the user types a Mano command (`mano start`, `mano spec`, `mano stories`, etc.), execute the matching skill in `_mano/skills/` and follow its contract. Do not treat Mano commands as shell commands or ask the user to run them manually.

For story implementation, follow the rules in `AGENTS.md` under "Implementing a story" and "Implementation Output Discipline."