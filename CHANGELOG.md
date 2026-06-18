# Changelog

A narrative history of Mano's releases — what each version is, why it exists, and what it doesn't do yet.

## 1.0.0 — Initial Release: June 18, 2026

Mano started from a simple frustration: heavyweight AI planning frameworks ask you
to think everything through upfront, generate large documents, and trust agents to
run with them. Mano takes the opposite bet — that software rarely moves in a straight
line, so planning should stay cheap to revise and the human should stay the judge at
every step. It is a supervised, à la carte planning protocol for coding agents:
small shippable phases, only the context the current phase needs, and artifacts that
are explicit, human-readable, and disposable when they stop being useful.

This first release makes Mano installable and settles its core surface after a long
period of refinement against real projects.

### Key Features
- **À la carte, not a pipeline** — a minimal path of a few commands; every other
  planning action (`spec`, `ux`, `rules`, `ui`) is optional context-tightening you
  run only when the current phase needs it.
- **Phases as the unit of work** — each phase is scoped, built, reviewed, and closed
  as one coherent, independently verifiable slice, with the human approving at each seam.
- **A thin implementer contract** — `mano dev` implements one story against its
  acceptance criteria and stops; one-line output, no narrative, no scope creep.
- **Action-named skills** — `mano start`, `mano spec`, `mano stories`, `mano review`,
  and more, each a focused constraint lens that reads only what it needs.
- **`npx mano-init install`** — one command drops Mano into any project; re-run it to update.
- **Token-efficient by design** — Mano loads one skill at a time rather than a whole
  pipeline, and keeps the implementer's per-story contract small, so the build loop
  spends its context on your code rather than on the framework.

### Limitations
- Single-threaded by design — one phase at a time; concurrent multi-team work on the
  same phase track isn't supported.
- No automated test/eval suite yet, so the framework's quality rests on human review.
- Behaviour depends entirely on the agent's instruction-following; smaller models can
  still drift, and the human remains the enforcer of scope and quality.
