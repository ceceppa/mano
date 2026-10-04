---
title: "Planning and implementation features"
description: "Explore Mano build mode, auto mode, document imports, team owners, tracks, languages, and hooks, and learn when each option helps your development workflow."
---

# Features

The loop — `start → spec → rules → stories → dev → review` — is the default and covers most phases. These are the parts you reach for when a project grows past it.

| | What it is | When you need it |
| --- | --- | --- |
| [Build mode](/features/build) | Implement a phase straight from its approved brief, no story files | The phase is small enough to hold in one contract |
| [Auto mode](/features/auto-mode) | Chain the commands you'd otherwise type, armed only by your scope approval | You've read enough briefs to trust their shape |
| [Import](/features/import) | Turn an existing PRD or document into a backlog, then stop | You already wrote the requirements somewhere else |
| [Team owners](/features/owners) | Namespace phases per person, so two people don't both scope "phase 7" | More than one person planning in one repo |
| [Tracks & filters](/features/tracks) | Narrow what a phase is allowed to contain | The backlog has absorbed several documents |
| [Languages](/features/languages) | Pick the language for chat, planning artifacts, and code separately | You don't want to plan, or ship, in English |
| [Hooks](/features/hooks) | Wire your own review checklist into any skill | You've made the same correction three phases running |

Everything here is optional. Nothing is on by default, and nothing arms itself.

## Owner JSON files

Mano saves portable settings and chain state in `_mano_output/[owner].json`. Each owner has a separate file that you can commit with the project.

| File | What it contains | Commit it? |
| --- | --- | --- |
| `_mano_output/alice.json` | Alice's mode, track, languages, and chain records by phase | Yes, to resume elsewhere |
| `_mano_output/.default.json` | The same settings for work without an owner | Yes, if used |
| `_mano_output/.local.json` | The owner selected in this checkout | No; Mano adds it to `_mano_output/.gitignore` |

Use these commands in your agent's chat to create or update the files:

```text
mano owner alice
mano mode auto
mano track "Option B"
mano language chat it build en-GB artefacts it
```

A new owner starts in `manual` mode with no track and no languages set. Selecting an existing owner restores that owner's saved settings. Bare `mano owner`, `mano mode`, `mano track`, and `mano language` show the effective values. `mano mode clear` resets the mode to `manual`; `mano track clear` resets the track to `null`; `mano language clear` resets all three languages to `null`, or only the channels you name. `mano owner clear` selects the unowned `.default.json` settings without deleting any owner's file.

An owner file with an approved chain in progress looks like this:

```json
{
  "version": 1,
  "owner": "alice",
  "mode": "auto",
  "track": "Option B",
  "language": { "chat": "it", "build": "en-GB", "artefacts": "it" },
  "phases": {
    "alice-phase-1": {
      "skipped": ["ux"],
      "run": {
        "actions": ["ui", "build"],
        "repairs": []
      }
    }
  }
}
```

| Field | Meaning |
| --- | --- |
| `version` | Settings format version; currently `1` |
| `owner` | Owner slug matching the filename; `null` in `.default.json` |
| `mode` | `manual` or `auto` |
| `track` | Active work track, or `null` for none |
| `language.chat` | Conversation language, e.g. `it` for Italian; missing or `null` keeps existing behaviour |
| `language.build` | Language for new implementation content, e.g. `en-GB` for UK English; missing or `null` keeps existing behaviour |
| `language.artefacts` | Language for new planning artifacts; missing or `null` falls back to `build`, then `chat`, then existing behaviour |
| `phases` | Only the newest phase’s chain record, keyed by its exact phase ID |
| `skipped` | Planning actions the human explicitly removed from this phase's chain |
| `run.actions` | Remaining approved actions, in order; a nonempty list ends with `build` or `dev` |
| `run.repairs` | Artifact actions already given an automatic repair attempt in this run |

`run: null` means there is no saved approval. A run with `"actions": []` means the approved chain has finished. These records accompany the phase artifacts and implementation ledgers; they do not replace them. Mano updates the chain fields as approved actions finish, so use the commands to manage them rather than reconstructing approval by editing JSON.

Agents obtain the effective languages by running `node _mano/scripts/settings.js language` from the project root. The command returns validated JSON with `language.chat`, `language.build`, and `language.artefacts`, resolving the selected owner. Missing `chat` and `build` values become `null`; missing or `null` `artefacts` falls back to `build`, then `chat`, then `null`; agents do not read the settings files themselves. Every skill runs this check before its first response or project write, including auto-chain handoffs and resumed work. English response templates retain their structure while their prose follows the chat language, including build and dev completion messages.

Set conversation, implementation, and planning languages independently with `mano language`. It creates the settings file if it does not exist yet, so it works on a fresh install:

```text
mano language chat it build en-GB artefacts it   # set several channels at once
mano language build en-GB                         # or just one
mano language clear artefacts                     # planning artifacts follow build again
mano language                                     # show the effective values
```

From a terminal, the same commands are `node _mano/scripts/language.js show|set|clear`. Every language needs its channel — `chat`, `build`, or `artefacts` — so a bare `mano language it` is refused rather than guessed. Values are language names or locale tags; quote a name with spaces (`mano language chat "Brazilian Portuguese"`). The artefacts language applies to briefs, specs, rules, UX flows, design briefs, stories, backlog entries, reviews, and ledger prose. The build language applies to product documentation, code identifiers and comments, tests, and product/UI text, including preview copy. The owner file example above produces Italian chat and planning artifacts with UK English implementation content — `mano language chat it build en-GB artefacts it`. Existing settings containing only `chat` and `build` remain valid; the command resolves the artefacts fallback without saving it into the settings file. Required machine-readable labels, commands, paths, and exact quotations stay unchanged. Changing a language does not translate existing files.

Older phase settings are compacted automatically, retaining the highest phase number per owner. Starting a newer chain replaces the previous record; attempts to update an older phase are rejected. Phase artifacts and implementation ledgers remain intact. Old Git settings cannot restore discarded history.

The local selection contains only:

```json
{ "owner": "alice" }
```

To continue on another computer:

1. Commit and push the owner JSON together with the phase artifacts and code.
2. Clone or pull the project on the other computer.
3. Run `mano owner alice` once in that checkout, then `mano continue`.

`MANO_OWNER`, `MANO_MODE`, and `MANO_TRACK` override the stored values for a shell or worktree without saving those overrides. Empty overrides are errors. Settings work without a Git repository; Git is only needed when you want to commit and share them.

Existing settings from older Mano versions migrate automatically when corresponding JSON state is missing. Existing JSON values win, including cleared settings and completed chains.
