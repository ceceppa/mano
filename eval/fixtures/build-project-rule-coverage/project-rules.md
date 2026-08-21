# Project Rules

## Documentation

**What:** Every public class ships with both documentation channels:

- A source documentation comment directly above the exported class declaration that gives the class's one-line purpose.
- A Markdown page at `docs/api/<kebab-case-class-name>.md` containing an overview, one minimal example, and the public methods.

**Why:** Package consumers need useful editor help and a browsable API reference when a public class becomes available.

**Pattern:** Link conceptually related public types from the source comment when relevant.
