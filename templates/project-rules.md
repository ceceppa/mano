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

### State machine for async operations
Client-side state management for data fetching must follow a state machine pattern with mutually exclusive states: `idle`, `loading`, `error`, `success`. Only one state is true at any time. Never mix states (e.g. `loading && error` should never both be true).
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

### Phase priorities

<!-- Uncomment and customise to ensure every phase includes certain types of work. -->
<!-- Skye will include at least one backlog item per listed category in her suggestion. -->
<!-- phase_priorities: bug, tech-debt -->

### Story completion

When you finish implementing a story, update its status to `done` in `_mano_output/phase-[N]/stories/README.md`. This is how Mano knows the phase is built and ready for review. Do not wait for manual confirmation — mark it done when the implementation is complete.

### Finding stories

When asked to implement a story (e.g. "implement story 3"), find the active phase by looking for the highest numbered `phase-[N]/` folder in `_mano_output/`. Read the story from `_mano_output/phase-[N]/stories/`. Always check the stories README index first to confirm the story exists and its current status.

---
