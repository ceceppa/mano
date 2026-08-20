# Design Brief — Signal Digest

<!-- sentinel: design-phase-1-must-survive -->

## Visual Direction

- **Style:** Quiet, typographic status report
- **Mode:** Light
- **Accessibility target:** WCAG 2.1 AA

## Colour Palette

| Role | Colour | Hex |
|------|--------|-----|
| Primary | Signal blue | `#2457D6` |
| Background | Paper | `#F7F8FC` |
| Surface | White | `#FFFFFF` |
| Text | Ink | `#172033` |

## Typography

- **Font family:** Inter, system-ui, sans-serif
- **H1:** 32px / 40px, 700
- **Body:** 16px / 24px, 400

## Screen Composition

### Phase 1 — Digest List

- **Purpose:** Read the digest top to bottom.
- **Sections (top to bottom):** Header; entry lines.
- **Shared components used:** EntryLine.
- **Layout / hierarchy notes:** One column, no chrome; the entry line carries all the information.

---

# Component Guide

## Text

### EntryLine

- Background: surface (`#FFFFFF`)
- Text: ink (`#172033`)
- Contrast: 13.0:1 ✅ AA
- Line height: 24px
