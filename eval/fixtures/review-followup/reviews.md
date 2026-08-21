# Phase Review — Tag Index

---

## Phase 1 Review — 2026-08-18

### Validation

- **Result:** Tagging works; removing a tag leaves it on screen until I reopen the note.

### Phase checks

| # | Phase promise | Result | What happened |
|---|---|---|---|
| E1a | Tag a note `recipes` then reopen the note: the tag `recipes` is still on it | passed | The tag survived a reopen. |
| E1b | Remove the tag `recipes` from that note then reopen it: no tag is shown | failed | The removed tag stayed visible until the note was reopened. |

### Questions

| # | Question | Answer |
|---|---|---|
| Q1 | Is one flat tag per note enough, or do readers immediately want nesting? | unanswered at close |

### Decision

- **Choice:** Not assessed

### Assumptions

| # | Assumption | Result | What showed this |
|---|-----------|---------|------------------------|
| A1 | Readers tag as they write rather than in a separate tidy-up pass. | accepted | Not ruled on; the phase closed on it. |

### Backlog changes

- bug Removed tag lingers until reload — raised by this review
