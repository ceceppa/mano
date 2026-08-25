# Backlog

## Core Product Principles

- Production-ready by default: a behaviour isn't complete just because its ideal
  case works — interruption, reversal, and property conflicts must all be
  defined, not left as edge cases.

## Items

### Motion interruption policy
- **Type:** feature
- **Context:**
  When a second motion targets a property a running motion already owns, both
  currently write to it. Add an explicit interruption policy the caller selects
  per motion — replace, retarget, reverse, queue, cancel, complete-current, or
  ignore-new — so the resulting property state is defined rather than a race.
  This is engine behaviour: the policy is chosen in code by the caller.
- **Status:** backlog

### Showcase category in the demo selector
- **Type:** feature
- **Context:**
  The demo selector currently offers two categories. Add a third, "Showcase",
  holding the existing Grid Showcase demo. Selecting it filters the list the
  same way the existing categories do. No new demos.
- **Status:** backlog

### Motion conflict debugger panel
- **Type:** feature
- **Context:**
  An editor panel for inspecting which motion owns a property and what the
  pending queue looks like. Deferred — heavyweight editor tooling.
- **Status:** backlog
