# Project Rules

## Module Format

**What:** Every module under `src/` is CommonJS: it requires its dependencies with `require()` and exports through `module.exports`.

**Why:** The package is consumed by an embedder that has no bundler.
