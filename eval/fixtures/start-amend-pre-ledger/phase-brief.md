# Phase Brief — Stage Chain — Phase 1

## Why This Phase

The project needs a tiny dependency-free stage chain that downstream examples can load without setup.

## Phase Goal

Consumers can load base and feature stage labels from two ordered CommonJS modules.

## Phase Scope

1. **Base stage** — a CommonJS module at `src/base-stage.js` whose export is the stage label `base`.
2. **Feature stage** — a CommonJS module at `src/feature-stage.js` that loads the base stage and exports the label `base+feature`.

## Not This Phase

- Any stage beyond feature, and any timing, logging, or debug output.

## Exit Criteria

1. **Module loading**
   a. Requiring `src/base-stage.js` returns the label `base`
   b. Requiring `src/feature-stage.js` returns the label `base+feature`

## Acknowledged Risks

- None.
