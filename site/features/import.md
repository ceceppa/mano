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

## Then what

Import stops on purpose. Scoping the first phase is still yours:

```
mano start
```

If you imported several documents, [`mano start from source`](/features/tracks) narrows the candidates to one of them.
