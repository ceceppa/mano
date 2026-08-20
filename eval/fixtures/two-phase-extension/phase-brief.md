# Phase Brief — Signal Digest — Phase 2

## Why This Phase

A reviewer reading a long digest cannot tell at a glance what still needs attention: every entry is one flat line in one flat list.

## Phase Goal

A reviewer opening the digest sees entries gathered under their status, in a fixed order, still rendered with the Phase 1 entry line.

## Phase Scope

1. **Status grouping** — a CommonJS module at `src/digest/group-entries.js` exporting `groupEntries(entries)`. It returns an array of `{ status, entries }` groups in the order `open`, `blocked`, `done`, leaves out any status with no entries, keeps the caller's order inside each group, and returns an empty array for an empty input.
2. **Digest rendering** — a CommonJS module at `src/digest/render-digest.js` exporting `renderDigest(entries)`. It returns a string in which each group contributes the heading line `## Open`, `## Blocked`, or `## Done`, followed by one line per entry of `- ` plus that entry's Phase 1 `formatEntry` output. Groups are separated by a single blank line, and an empty input renders an empty string.
3. **Public surface** — `src/digest/index.js` also exports `groupEntries` and `renderDigest`, and keeps exporting `formatEntry` exactly as Phase 1 does.

## Not This Phase

- Sorting, filtering, colour, HTML output, or any new entry field.

## Exit Criteria

1. **Status grouping**
   a. `groupEntries` returns groups ordered open, blocked, done, and omits a status that has no entries
   b. `groupEntries` returns an empty array for an empty entry list
2. **Digest rendering**
   a. `renderDigest` writes each group's heading line and then one `- ` line per entry, using the Phase 1 entry format unchanged
3. **Public surface**
   a. Requiring `src/digest/index.js` exposes `formatEntry`, `groupEntries`, and `renderDigest`

## Acknowledged Risks

- None.
