# Project Rules

The team agrees to follow these architectural decisions, styling standards, and workflow patterns. This list can be extended or modified as required down the line. The coding agent must follow these rules without exception on every single story.

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

## Accessibility

<!-- Record the agreed accessibility baseline here. Luna may seed the `Accessibility level:` line if it is still blank during `mano ui`. Alex maintains the rest of this section. Example:

Accessibility level: WCAG 2.1 AA

### Interaction basics
- Minimum touch target: 44×44px.
- Visible focus indicators are required for all interactive elements.
- Text and UI labels must meet the selected contrast target.
-->

---

## Workflow

### Story mode

<!-- Uncomment one to stop Marco asking every time: -->
<!-- story_mode: behaviour -->
<!-- story_mode: enriched -->

### Phase priorities

<!-- Uncomment and customise to ensure every phase includes certain types of work. -->
<!-- Skye will include at least one backlog item per listed type in her suggestion. -->
<!-- Valid types: bug, refinement, feature, tech-debt, test, spec-gap, rule-gap -->
<!-- phase_priorities: bug, tech-debt -->

### Story completion

When you finish implementing a story, update its status to `done` in `_mano_output/phase-[N]/stories/README.md`. This is how Mano knows the phase is built and ready for review. Do not wait for manual confirmation — mark it done when the implementation is complete.

### Finding stories

When asked to implement a story (e.g. "implement story 3"), find the active phase by looking for the highest numbered `phase-[N]/` folder in `_mano_output/`. Read the story from `_mano_output/phase-[N]/stories/`. Always check the stories README index first to confirm the story exists and its current status.

**Before implementing any story, read this entire `project-rules.md` file.** Every rule applies to every story — even if the story's Implementation Reference doesn't mention a specific rule. The Implementation Reference highlights the most relevant rules, but it is not exhaustive.

---
