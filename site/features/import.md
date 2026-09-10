---
title: "Import requirements into a development backlog"
description: "Turn an existing PRD or requirements document into a Mano backlog, preserving source requirements before you choose and approve a phase to build."
---

# Import a document

```
mano import prd.md
```

You already have a PRD, a spec, a long issue. You don't want to retype it into a conversation.

Import turns the document into a backlog and **stops**. It doesn't scope, decide, or read your source to guess at work — it converts what the document says into items.

## Project-wide directives don't get lost

The part a document-to-backlog conversion usually drops:

> A document's project-wide technical directives — a runtime or version constraint, a module system, a folder structure, a file-naming scheme, where tests live — belong to every item and therefore to none, which is exactly how they vanish between the document and the first line of code.

Those become their own backlog items, carrying the directive verbatim, so `mano spec` and `mano rules` pick them up later instead of losing them.

## Updating an existing backlog

Import can merge a new brief into an existing backlog. Added detail updates the existing item; new work becomes a new item. If the brief contradicts planned work, import surfaces the conflict and can mark an item `rejected` once you authorize that direction. An explicit instruction to replace the old direction already counts; a general merge request does not.

Only items with `Status: backlog` can be rejected. They stay in the backlog with the reason and source document recorded. Scoped and completed work stays unchanged, with conflicts handed to `mano review`. Omitting an older feature from a new brief does not reject it.

## Then what

Import stops on purpose. Scoping the first phase is still yours:

```
mano start
```

If you imported several documents, [`mano start from source`](/features/tracks) narrows the candidates to one of them.
