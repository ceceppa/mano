# Phase Brief — Label Registry — Phase 1

## Why This Phase

A downstream example needs a tiny dependency-free label registry it can require without any setup.

## Phase Goal

Consumers can add, list, de-duplicate, and clear registry labels through one CommonJS module, and read the same labels as one formatted line through a separate module.

## Phase Scope

1. **Registry core**
   a. **List** — a CommonJS module at `src/registry.js` exports `list()`, which returns the registered labels as an array, in the order they were added.
   b. **Add** — `src/registry.js` exports `add(label)`, which appends the label and returns the new number of registered labels.
   c. **Reject a duplicate** — `add(label)` leaves the registry unchanged and returns `-1` when that exact label is already registered.
   d. **Clear** — `src/registry.js` exports `clear()`, which removes every label and returns how many it removed.
2. **Formatting**
   a. **Joined line** — a CommonJS module at `src/format.js` exports `line()`, which reads the registry and returns its labels joined by `, ` (an empty registry returns an empty string).

## Not This Phase

- Saving the registry to disk, sorting or filtering options, and any command-line entry point.

## Exit Criteria

1. **Registry**
   a. Call `add('alpha')` then `list()`: the result is `['alpha']` and the `add` call returned `1`
   b. Call `add('alpha')` a second time: it returns `-1` and `list()` still returns `['alpha']`
   c. Call `add('alpha')`, `add('beta')`, then `clear()`: `clear()` returns `2` and `list()` returns `[]`
2. **Formatting**
   a. Call `add('alpha')`, `add('beta')`, then `line()`: the result is the string `alpha, beta`
   b. Call `line()` on an empty registry: the result is the empty string

## Acknowledged Risks

- None.
