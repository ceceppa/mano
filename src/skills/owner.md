---
name: mano-owner
description: Use to show, set, or clear the local owner slug that opts this repository clone into owner-scoped Mano phases for parallel team work.
---

# `mano owner` — Phase Ownership

Prefix every message with `[mano owner]:`.

This command configures routing; it does not create, rename, migrate, scope, or close a phase.

## Activation

- `mano owner` or `mano owner show` → run `node _mano/scripts/owner.js show`.
- `mano owner <slug>` or `mano owner set <slug>` → run `node _mano/scripts/owner.js set <slug>`.
- `mano owner clear` → run `node _mano/scripts/owner.js clear`.

Relay the script result and stop. If it fails, report the exact error; do not edit settings JSON or phase folders by hand.

## Contract

- Ownership is opt-in. With no configured slug, all phase-scoped commands keep using legacy `_mano_output/phase-N/` folders and `in-phase-N` backlog statuses.
- With a configured slug such as `alice`, phase-scoped commands use `_mano_output/alice-phase-N/` and `in-alice-phase-N` within that owner's independent number sequence.
- The slug is a stable team handle, not `whoami`, a machine account, or an email address.
- Mode, track, remaining approved actions, skips, and repair attempts live in committed `_mano_output/[owner].json` files. Without an owner, they use `_mano_output/.default.json`. Only the selected owner stays in ignored `_mano_output/.local.json`. Environment variables override the stored values for a shell or worktree.
- Settings work without a Git checkout. Existing local Git config values migrate automatically when JSON state is missing; JSON takes precedence.
- Two people may configure the same slug to hand over or pair on the same phase. Different slugs select independent phase sequences.
- Clearing the slug returns this repository clone to legacy `phase-N` routing. Existing owned folders remain untouched.
- Ownership selects work; it does not provide merge isolation. Teammates still use branches/worktrees and coordinate changes to shared backlog, spec, rules, design, and review files.

## Output

```text
[mano owner]: [script result without its `[mano owner]` prefix]
```
