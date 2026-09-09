---
title: "Tracks and filters for focused phase scope"
description: "Use Mano tracks and source filters to focus phase planning on an experiment or imported document while keeping the rest of your backlog available."
---

# Tracks & filters

A backlog that has absorbed three imported documents and two rounds of review feedback will happily offer `mano start` fifty candidates. Two filters cut that down.

## By what you're currently working on

```
mano track "offline-mode"
```

A track is a named direction or experiment. Once set it applies to every `mano start` automatically, until you clear it:

```
mano track clear
```

Borrow a different one for a single run:

```
mano start from track "billing-rewrite"
```

### Where the track lives

Mode, track, remaining approved actions, skips, and repair attempts live in committed `_mano_output/[owner].json` files. Without an owner, they use `_mano_output/.default.json`. Only the selected owner stays in ignored `_mano_output/.local.json`. Environment variables override the stored values for a shell or worktree. See [Owner JSON files](/features/#owner-json-files) for the file structure, commands, and steps to resume on another computer.

In chat:

```
mano track                  # what this clone is set to
mano track "offline-mode"   # set it
mano track clear            # back to untracked planning
```

From a terminal:

```bash
node _mano/scripts/track.js show   # read it
export MANO_TRACK="offline-mode"    # override, for agents launched from this shell
```

A track is 1–120 printable characters on one line — a label you'd recognise, not a slug.

The setting travels with the owner JSON, and `mano start` records `**Track:** [name]` in the phase brief, so the phase itself carries the track into review even on a clone that has none configured. It also tags new imports and conversational Start items.

## By where an item came from

```
mano start from source "onboarding-prd.md"
```

Only items whose backlog `Source` contains that text become phase candidates. Useful after [importing](/features/import) several documents.

`from source` is a per-run flag, not a setting — there's nothing to clear, and nothing is stored. Combine the two when both origin and direction matter.

Same for `mano start from track "..."`: it borrows a track for one run and leaves `mano.track` untouched.

## What a filter isn't

Neither filter is an approval, a priority, or an epic. They narrow what Mano *proposes* — `mano start` still suggests a subset, still runs its contradiction checks, and still waits for you to approve the scope.

No matches means the filter is too narrow. Mano won't quietly fall back to the whole backlog.
