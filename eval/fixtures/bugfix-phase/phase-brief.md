# Phase Brief — Notekeeper — Phase 2

## Why This Phase

Phase 1 shipped note creation and listing, but two bugs make the list unreliable: notes lose their order after a restart, and deleting a note sometimes removes the wrong one. This phase fixes both so the list can be trusted.

## Vision

The note list shows what you saved, in the order you saved it, and deleting a note removes exactly that note. Nothing surprises the user.

## Design Principle

Correctness before new features — the list must be trustworthy before anything is built on top of it.

## Phase Goal

Notes persist in creation order across restart, and deleting a note removes exactly the selected note.

## Phase Scope

- Fix: note order is preserved after closing and reopening the app
- Fix: deleting a note removes the selected note, not an adjacent one

## Exit Criteria

1. Order persistence
   - Create three notes, close and reopen the app: notes appear in the original creation order
2. Correct deletion
   - Delete the middle note of three: only that note disappears, the other two remain unchanged

## Assumption Log

| Assumption | Risk if wrong |
|---|---|
| Notes are stored locally with a stable created-at timestamp | If timestamps collide, order is non-deterministic |

## Acknowledged Risks

- The delete bug may be an index-vs-id mismatch; fixing it could touch the list-rendering key
