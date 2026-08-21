# Phase Brief — Label Registry — Phase 1

## Why This Phase

A downstream example needs a tiny dependency-free label registry, and the registry must not grow without bound.

## Phase Goal

Consumers can add, list, and clear registry labels through one CommonJS module, and the registry keeps only its most recent labels once it is full.

## Phase Scope

1. **Registry core**
   a. **List** — a CommonJS module at `src/registry.js` exports `list()`, which returns the registered labels as an array, in the order they were added.
   b. **Add** — `src/registry.js` exports `add(label)`, which appends the label and returns the new number of registered labels.
   c. **Clear** — `src/registry.js` exports `clear()`, which removes every label and returns how many it removed.
2. **Capacity**
   a. **Drop the oldest** — once the registry is full, `add(label)` still registers the new label and drops the oldest one, so `list()` never returns more than the registry's maximum size.

## Not This Phase

- Saving the registry to disk, sorting or filtering options, and any command-line entry point.

## Exit Criteria

1. **Registry**
   a. Call `add('alpha')` then `list()`: the result is `['alpha']` and the `add` call returned `1`
   b. Call `add('alpha')`, `add('beta')`, then `clear()`: `clear()` returns `2` and `list()` returns `[]`
2. **Capacity**
   a. Add one more label than the registry's maximum size: `list()` returns the newest labels only, and the first label added is gone

## Acknowledged Risks

- None.
