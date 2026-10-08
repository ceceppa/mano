# Design Brief — Preview Service

<!-- sentinel: design-phase-1-must-survive -->

## Visual Direction

- **Style:** Calm, content-first workspace
- **Mode:** Light
- **Accessibility target:** WCAG 2.1 AA

## Colour Palette

| Role | Colour | Hex |
|------|--------|-----|
| Primary | Harbour blue | `#2F5DA8` |
| Background | Mist | `#F4F6F9` |
| Surface | White | `#FFFFFF` |
| Text | Slate | `#1D2633` |

## Screen Composition

### Phase 1 — Preview Panel

- **Purpose:** Show the thumbnails of the current folder.
- **Sections (top to bottom):** Panel header; thumbnail grid.
- **Shared components used:** Thumbnail, SettleOutline.
- **Layout / hierarchy notes:** The grid fills the panel; thumbnails keep their aspect ratio.

---

# Component Guide

## Feedback

### SettleOutline

- Stroke: 2px primary (`#2F5DA8`)
- Shown only for the moment a thumbnail lands in its final position, then fades out over 150ms.
- Never shown while the thumbnail is still moving.
