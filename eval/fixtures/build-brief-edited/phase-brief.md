# Phase Brief — Stage Chain — Phase 1

## Why This Phase

The project needs a tiny dependency-free stage chain that downstream examples can load without setup.

## Phase Goal

Consumers can load base, feature, and release stage labels from three ordered CommonJS modules.

## Phase Scope

1. **Base stage** — a CommonJS module at `src/base-stage.js` whose export is the stage label `base`.
2. **Feature stage** — a CommonJS module at `src/feature-stage.js` that loads the base stage and exports the label `base+feature`.
3. **Release stage** — a CommonJS module at `src/release-stage.js` that loads the feature stage and exports the label `base+feature+release`.

## Not This Phase

- Any stage beyond release. Timing and logging are fine after all.

## Exit Criteria

1. **Module loading**
   a. Requiring `src/base-stage.js` returns the label `base`
   b. Requiring `src/feature-stage.js` returns the label `base+feature`
   c. Requiring `src/release-stage.js` returns the label `base+feature+release`

## Acknowledged Risks

- None.
