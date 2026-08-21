# Phase Brief — Word Count — Phase 1

## Why This Phase

A writing tool needs a dependency-free way to count what is in a draft before anything else can display it.

## Phase Goal

Consumers can count the words and the non-whitespace characters of a string through one CommonJS module.

## Phase Scope

1. **Counting**
   a. **Words** — a CommonJS module at `src/count.js` exports `words(text)`, which returns how many whitespace-separated words the text holds
   b. **Characters** — `src/count.js` also exports `characters(text)`, which returns how many characters the text holds, not counting whitespace

## Not This Phase

- Reading counts from a file, live updates while typing, and any command-line entry point.

## Exit Criteria

1. **Counting**
   a. Call `words('one two three')`: the result is `3`
   b. Call `words('')`: the result is `0`
   c. Call `characters('one two')`: the result is `6`

## Validation Plan

### Questions

- **Q1.** Is a character count that ignores whitespace the number a writer actually wants?

### Try

- Paste a paragraph you actually wrote and compare both counts against your editor's

## Assumption Log

| ID | Assumption | Risk if wrong |
|---|---|---|
| A1 | A writer checks the counts occasionally rather than watching them change as they type. | The counts need to be live, which is a different phase. |

## Acknowledged Risks

- None.
