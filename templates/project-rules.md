# Project Rules

These rules apply to every story and every implementation. The coding agent must follow them without exception.

---

## Components

<!-- Define shared components here. Example:

### Button

Create a shared `Button` component.

**Variants:** primary, secondary, destructive, ghost.

**Rules:**
- All buttons must use this component — no raw Pressable or TouchableOpacity.
- Minimum touch target: 44×44pt.
-->

---

## Patterns

<!-- Define coding patterns here. Example:

### Theme object
All design tokens must be defined in a single theme file. No hardcoded values.

### One responsibility per component
If a component handles data fetching, state, and rendering, split it.
-->

---

## Architecture

<!-- Define architectural rules here. Example:

### No inlined native code
Keep native files as actual files, not template strings in JS/TS.
-->

---

## Workflow

### Story mode

<!-- Uncomment one to stop Marco asking every time: -->
<!-- story_mode: behaviour -->
<!-- story_mode: enriched -->

### Story completion

When you finish implementing a story, update its status to `done` in `_mano_output/phase-[N]/stories/README.md`. This is how Mano knows the phase is built and ready for review. Do not wait for manual confirmation — mark it done when the implementation is complete.

---

<!-- Add more sections as needed: Accessibility, Testing, Naming, etc. -->
