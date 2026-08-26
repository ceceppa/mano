# Phase Brief — Preview Service — Phase 1

## Why This Phase

Thumbnails must settle into their final layout without visibly jumping when a panel resizes.

## Phase Goal

Someone resizing the preview panel sees every thumbnail move smoothly to its final position.

## Phase Scope

1. **Automatic thumbnail settling**
   a. **Visual settle** — a panel resize moves each thumbnail from its previous position to the final one.
   b. **Supported boundaries** — settling applies to thumbnails inside one panel.

## Not This Phase

- Manual settle-authoring forms.
- Thumbnails outside the panel.

## Exit Criteria

1. **Automatic settling**
   a. Resize the preview panel: every thumbnail reaches its final position without a visible jump.
   b. Inspect the settled panel: the final arrangement is the one the layout engine chose.

## Validation Plan

### Questions

- **Q1.** Is the settling clear enough to verify by watching the panel resize?

### Try

- Resize the preview panel and watch the thumbnails settle.

## Assumption Log

| ID | Assumption | Risk if wrong |
|---|---|---|
| A1 | One panel is enough to establish settling behaviour. | A later case could require rework rather than extension. |

## Acknowledged Risks

- Resize edge cases may need a follow-up refinement.
