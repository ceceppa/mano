# PRD — Ledger CLI (`ledger`)

## What it is

A single-user command-line expense ledger. The core experience answers one
question: **"what have I spent this month?"** — one number, the sum of every
expense the user recorded with a date inside the current calendar month.

## Who it's for

People who track a handful of expenses a month and do not want an app, an
account, or a sync service.

## Runtime & tooling

* **Runtime:** Node.js (v20 or newer).
* **Dependencies:** zero external npm packages.

## Project directory structure

```text
ledger/
├── src/
│   ├── store.js
│   └── cli.js
└── test/
    └── store.test.js
```

## Features

- **Record an expense** — the user supplies an amount, a category, and an
  optional note; the ledger stamps it with the current date.
- **The month total** — the sum of every recorded expense dated inside the
  current calendar month, printed as a single number.
- **Category breakdown** — the same month's expenses subtotalled per category,
  one line per category that has at least one expense.
- **Expense history** — every recorded expense, newest first, with its date,
  amount, category, and note.

## Success criteria

- A recorded expense is counted in the month total the next time it is printed.
- The month total prints `0` rather than nothing when the month has no expenses.
- An expense dated in a previous month never counts toward the current month's
  total, but still appears in the history.

## Notes

- Should feel instant — no spinners, no network calls, no startup wait.
- Store the expenses in a plain JSON file; there is no database and no account system.
- Budgets and recurring expenses can come later.
