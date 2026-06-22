# Project Rules

## Testing Expectations

**What:** Add tests for the behaviour introduced or changed by each story, including edge cases when relevant.

**Why:** Keeps stories verifiable without separate test-only work.

**Pattern:**
- Behaviour test: expected successful path
- Edge test: invalid, empty, missing, or boundary input when relevant
- Regression test: only when fixing a known defect

## Naming

- Components `PascalCase`, functions `camelCase`, files match the component name.

## Architecture

- Storage access goes through a single `notesStore` module. Screens never touch AsyncStorage directly.
