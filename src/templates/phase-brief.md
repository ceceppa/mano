# Phase Brief — [Project Name] — Phase [N]

<!-- Owner-scoped mode only: add `**Owner:** [slug]` below. Omit it entirely for default phase-N mode. -->
<!-- Active work-track only: add `**Track:** [name]` below. Omit it entirely when no track is selected. -->

<!-- Self-contained. Everything needed to understand this phase is here. -->

## Why This Phase

<!-- One or two sentences explaining why this phase should happen now and what it makes possible. -->

## Vision

<!-- Max 3 sentences. -->

## Design Principle

<!-- One sentence. The decision filter. -->

## Core Product Principles

<!-- Optional. Include only principles from the backlog that matter for this phase. Keep short and human-readable. -->

-
-

## Phase Goal

<!-- One sentence. The single most important outcome. If you have to cut scope, this survives. -->

## Phase Scope

<!-- What ships. A numbered list, in the order the items should be built. Lead each item with a short bolded title, then an em dash, then the behaviour-level line. The number is that item's stable address for the whole phase (`mano build` addresses item 2 as `S2`), and the bolded lead is the label its progress ledger shows, so neither is decoration. An item with no bolded lead is still valid — its full text becomes the ledger label. Keep the whole brief concise: target roughly 250-500 words total. -->

1. **[Short title]** — [what ships, stated as behaviour]
2. **[Short title]** — [what ships, stated as behaviour]
3. **[Short title]** — [what ships, stated as behaviour]

## Not This Phase

<!-- The negative of Phase Scope: capabilities the selected items imply but this phase does NOT ship, slices deferred during scoping, and adjacent work a reader would assume is included. One behaviour-level line each — what is excluded, not how. Keeps the implementer and `mano stories` from widening the phase by inference. Omit only when nothing was deferred or excluded. -->

-
-

## Exit Criteria

<!-- What a real person can do when this phase is done. Exactly two levels: a numbered category, then lettered `a.` / `b.` / `c.` leaves, each one action and its result separated by a colon. Never use arrows. Every leaf is separately addressable (`mano build` addresses them as `E1a`, `E2b`) and separately provable, so a criterion that would need a third level folds that detail into its own leaf text instead. -->

1. **[Category]**
   a. [action]: [result]
2. **[Category]**
   a. [action]: [result]
   b. [action]: [result]

## Validation Plan

<!-- This plan captures learning. Exit Criteria still captures every promised result. -->

### Questions

- [One concrete question per bullet. Every question needs a matching test below.]

### Try

- [What the human will use, show, play, or measure to answer a question]
- [What result the human will watch for]

## Assumption Log

| Assumption | Risk if wrong |
|---|---|
| | |

## Acknowledged Risks

-
-

## Stated Technical Preferences

<!-- Pass-through appendix, not part of the phase narrative. Include ONLY if the source input explicitly stated a stack, framework, storage, auth, or other technical directive. Transcribe each strictly verbatim — quote the source sentence unchanged, one per line. Do not paraphrase, evaluate, rank, or tidy. `mano start` is a courier here, not an editor. Omit this whole section if the source stated no technical preference — never invent one to fill it. This is the single durable channel for stated tech directives across a context reset; `mano spec` evaluates them and must flag any override. -->

<!-- Verbatim from the source; not scoped or decided by `mano start`. `mano spec` evaluates these and must flag any override. -->

-

<!-- Future work, deferred items, and ideas live in _mano_output/backlog.md — not here. -->
