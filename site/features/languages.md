---
title: "Languages for chat, code, and planning artifacts"
description: "Use mano language to choose the language Mano speaks in chat, writes planning artifacts in, and uses for code, tests, and product text, each set independently."
---

# Languages

Mano tracks three languages, and each can be set on its own:

| Channel | What it covers |
| --- | --- |
| `chat` | The conversation: explanations, questions, progress updates, hand-backs |
| `artefacts` | New planning prose: briefs, specs, rules, UX flows, design briefs, stories, backlog entries, reviews, ledger prose |
| `build` | New implementation content: code identifiers and comments, tests, product documentation, product/UI text |

Leave all three unset and Mano behaves as it always has.

## Setting them

In chat:

```
mano language chat it                       # one channel
mano language chat it build en-GB artefacts it   # several at once
mano language chat "Brazilian Portuguese"
mano language                               # show what's in effect
```

Every language needs its channel name in front of it. `mano language it` on its own is refused, because "Italian for what?" is exactly the question Mano shouldn't answer for you. Values are language names or locale tags. Quote a name that has spaces in it.

A common split is to talk and plan in your own language and keep the code in English:

```
mano language chat it artefacts it build en
```

## Clearing

```
mano language clear                   # all three back to unset
mano language clear artefacts         # just one
mano language clear build artefacts   # or a few
```

An unset `artefacts` follows `build`, then `chat`. So if you only ever set `chat` and `build`, planning artifacts quietly take the `build` language. Set `artefacts` explicitly when you want the planning documents to match the conversation instead.

## Where it lives

Languages sit next to mode and track in `_mano_output/[owner].json`, or `_mano_output/.default.json` with no owner. `mano language` creates that file if it isn't there yet, so it's a fine first command on a fresh install. Each [owner](/features/owners) has their own languages, and the file travels with the project when you commit it. See [Owner JSON files](/features/#owner-json-files) for the full file layout.

From a terminal:

```bash
node _mano/scripts/language.js show            # what's in effect
node _mano/scripts/language.js set chat it     # set one channel
node _mano/scripts/settings.js language        # the resolved JSON every skill reads
```

## What it doesn't do

Changing a language affects what gets written from now on. Mano never translates existing artifacts, finished stories, or code just because the setting changed.

Commands, file paths, required headings and status labels, external API names, and anything you said that Mano quotes back stay exactly as they are, whatever the language.
