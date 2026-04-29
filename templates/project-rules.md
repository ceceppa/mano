# Project Rules

The team agrees to follow these architectural decisions, styling standards, and workflow patterns. This list can be extended or modified as required down the line. The coding agent must follow these rules without exception on every single story.

---

## Components

<!-- Define shared components here only when the current project genuinely needs them.

Possible uses:
- Repeated interactive elements that should stay visually and behaviorally consistent
- Reusable form controls with project-specific accessibility or validation requirements
- Cross-screen UI building blocks that would otherwise drift
- Contracts from the design brief that now need explicit implementation rules

Do not duplicate the design brief's shared-component inventory here. If `design-brief.md` already names a component and this section has no extra implementation rule to add, leave it in the design brief only.

For each shared component, describe:
- what it is
- when it must be used
- any required variants, props, accessibility semantics, or constraints that the coding agent must follow
-->

---

## Patterns

<!-- Define coding patterns here only when they are useful for this project now.

Possible uses:
- State and data-fetching boundaries
- Token or theme management if the project needs centralized design values
- Error-handling or form-handling conventions
- Extraction thresholds for when UI should become shared
-->

---

## Architecture

<!-- Define architectural rules here when the stack or project shape requires them.

Possible uses:
- Routing or entrypoint boundaries imposed by the framework
- Native/web/client-server separation rules
- File placement rules for services, modules, or screen containers
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



### Story completion

When you finish implementing a story, update its status to `done` in `_mano_output/phase-[N]/stories/README.md`. This is how Mano knows the phase is built and ready for review. Do not wait for manual confirmation — mark it done when the implementation is complete.

### Finding stories

When asked to implement a story (e.g. "implement story 3"), find the active phase by looking for the highest numbered `phase-[N]/` folder in `_mano_output/`. Read the story from `_mano_output/phase-[N]/stories/`. Always check the stories README index first to confirm the story exists and its current status.

Before implementing the requested story, check whether any earlier story in the index is still `pending`. Treat numbered stories and lettered insertions as ordered work unless the README or story notes explicitly say otherwise. If an earlier story is still pending, stop and tell the user which story would be skipped. Do not implement the later story unless the user explicitly confirms they want to bypass the suggested order.

The story file is the primary implementation contract. Read `project-rules.md` when the story explicitly references a rule here or when something is still ambiguous after reading the story and any mandatory tech-spec pre-read.

---
