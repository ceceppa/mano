# Phase Brief — Signal Digest — Phase 1

## Why This Phase

There is no way to put a digest entry on screen at all, so nothing downstream can be built or reviewed.

## Phase Goal

A reviewer can see one digest entry rendered as a single line.

## Phase Scope

1. **Entry line** — a CommonJS module at `src/digest/format-entry.js` exporting `formatEntry(entry)`, which returns the entry's title, `" — "`, then its status.
2. **Public surface** — `src/digest/index.js` re-exports `formatEntry` as the package's only public entry point.

## Not This Phase

- Grouping, sorting, or filtering entries.
- PHASE-1-ONLY-CANARY kestrel-spike-parked: the discarded Kestrel column layout is recorded here only so Phase 1 reviewers know why it went away. It is settled, it is not carried forward, and no later phase has any reason to read it.

## Exit Criteria

1. **Entry line**
   a. `formatEntry` returns the title, `" — "`, and the status, in that order
2. **Public surface**
   a. Requiring `src/digest/index.js` exposes `formatEntry`

## Acknowledged Risks

- None.
