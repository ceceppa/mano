# Backlog

## Core Product Principles

- The tool should feel predictable; surprising behaviour is a defect.

## Items

### Group presets in the picker
- **Type:** feature
- **Context:**
  The preset picker is one flat list. Group the presets under headings so a
  long list stays navigable. Presentation only — no change to what a preset
  does or how presets are stored.
- **Status:** backlog

### Predictable cancellation for in-flight operations
- **Type:** refinement
- **Context:**
  Cancelling an operation mid-flight leaves partial state behind, so a
  restart can pick up values from the run that was cancelled. Needs a
  cancellation policy, clear ownership of the state each operation touches,
  and isolation between concurrent runs.
- **Status:** backlog

### Retired spike: hand-rolled preset importer CANARY-BACKLOG-DIRECT-READ
- **Type:** tech-debt
- **Context:**
  Closed exploration; kept only as history. The projection never surfaces
  resolved items, so this title can reach a transcript only if the agent
  opened backlog.md directly instead of using SCOPE INPUT.
- **Status:** resolved
