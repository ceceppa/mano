# Tech Spec — Signal Digest

<!-- sentinel: spec-phase-1-must-survive -->

## Stack

- Node.js 18+, CommonJS, no runtime dependencies.
- Source lives under `src/digest/`. One exported function per module.

## Entry Shape

An entry is a plain object: `{ title: string, status: "open" | "blocked" | "done" }`.
`title` is free text. `status` is exactly one of those three values; anything else is a caller error and is not defended against inside the digest modules.

## Public API

- `formatEntry(entry) -> string`, in `src/digest/format-entry.js`, returns the title, a space, an em dash, a space, then the status. The separator is `" — "` and nothing else formats an entry line.
- `src/digest/index.js` is the package's only public entry point and re-exports every public function.

## Out of Scope

- Persistence, HTTP transport, HTML output, and colour.
