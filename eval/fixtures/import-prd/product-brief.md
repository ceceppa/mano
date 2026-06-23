# Product Brief — Tilde

## What it is

Tilde is a personal reading tracker. The core experience answers one question:
**"what should I read next?"** — a single prioritized suggestion drawn from the
user's own to-read list, never a feed of recommendations from strangers.

## Who it's for

Solo readers who keep a backlog of books and lose track of what to pick up next.

## Features

- **Add a book** to the to-read list with title, author, and an optional priority note.
- **Mark a book as finished**, which removes it from the to-read list and records the finish date.
- **The next-read suggestion**: the app surfaces one book from the to-read list as the
  thing to read next.
- **Reading history**: a list of finished books with their finish dates.

## Success criteria

- A user can add a book and immediately see it counted in their to-read list.
- The next-read suggestion is never empty while at least one unfinished book exists.
- Finished books never appear in the to-read list again.

## Notes

- Should feel fast and calm — no social features, no notifications, no streaks or guilt mechanics.
- Use a local SQLite database; this is an offline-first app with no account system.
- Recurring/series handling (book 2 of a series auto-suggested after book 1) can come later.
