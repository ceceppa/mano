# Project Rules

<!-- sentinel: rules-phase-1-must-survive -->

Accessibility level: WCAG 2.1 AA

## Module Shape

**What:** Every module under `src/digest/` is CommonJS, exports its public functions through `module.exports`, and carries a one-line documentation comment directly above each exported function.

**Why:** The digest is read far more often than it is changed, and the comment is the only editor help a consumer gets in a dependency-free package.

**Pattern:** One responsibility per file; the filename is the kebab-case form of the function it exports.

## Composition

**What:** A module that needs an existing behaviour requires it; it never re-implements or copies it.

**Why:** The entry line format is defined once. A second copy is a second thing to keep in step.

## Testing

**What:** Every exported function ships a Node built-in test (`node:test` + `node:assert`) at `spec/<module-name>.spec.js`, covering the documented behaviour and its empty-input case. `npm test` runs them.

**Why:** The package has no runtime dependencies, so its own test runner should add none either.
