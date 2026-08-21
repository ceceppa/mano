# Phase Brief — Stage Chain — Phase 1

## Why This Phase

Downstream examples load the stage chain and must not hang when a stage is slow to resolve.

## Phase Goal

Consumers can load base and feature stage labels, and a slow stage gives up rather than hanging.

## Phase Scope

1. **Base stage** — a CommonJS module at `src/base-stage.js` whose export is the stage label `base`.
2. **Feature stage with a load timeout** — a CommonJS module at `src/feature-stage.js` that loads the base stage, exports the label `base+feature`, and gives up after a short wait if the base stage does not resolve.

## Not This Phase

- Any stage beyond feature.

## Exit Criteria

1. **Module loading**
   a. Requiring `src/base-stage.js` returns the label `base`
   b. Requiring `src/feature-stage.js` returns the label `base+feature`
2. **Slow stage**
   a. When the base stage does not resolve, requiring `src/feature-stage.js` gives up and reports the timeout

## Acknowledged Risks

- None.
