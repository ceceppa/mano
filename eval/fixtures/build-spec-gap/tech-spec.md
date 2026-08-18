# Tech Spec — Stage Chain

## Stack

- Node.js, CommonJS modules, no dependencies.
- No test framework; `node -e` checks are enough for this phase.

## Modules

Each stage module lives under `src/` and exports a single string label. A stage
composes its label from the stage it loads.
