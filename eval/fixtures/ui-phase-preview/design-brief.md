# Design Brief — Signal Desk

<!-- sentinel: cumulative-brief-phase-1-must-survive -->

## Visual Direction

- **Style:** Calm, editorial operations desk
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

### Phase 1 — Source Queue

- **Purpose:** Review newly connected sources.
- **Sections (top to bottom):** Header; source cards; connect action.
- **Shared components used:** InsightCard; PrimaryButton.
- **Layout / hierarchy notes:** One-column queue with the action held in the header.

---

# Component Guide

## Buttons

### PrimaryButton

- Background: primary (`#2457D6`)
- Text: white (`#FFFFFF`)
- Contrast: 6.2:1 ✅ AA
- Height: 44px

## Cards / List Items

### InsightCard

- Background: surface (`#FFFFFF`)
- Text: ink (`#172033`)
- Contrast: 13.0:1 ✅ AA
- Padding: 20px
