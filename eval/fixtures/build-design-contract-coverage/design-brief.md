# Design Brief — PulseKit

## Visual Language

A single dark surface with one accent. Every screen is assembled from the shared components under `src/components/` — `PanelHeader` and `SegmentedControl` are the only chrome a screen may use; a screen never builds its own header or its own row of window buttons.

## Screen Composition

### phase-1 — Latency Screen

1. **PanelHeader** — the shared header carries the service name as its title and "Latency" as its subtitle.
2. **Reading** — the latency for the selected window, large, directly under the header.
3. **SegmentedControl** — the shared window selector presents `1h`, `24h`, and `7d`; the selected window reads through the component's own indicator, not a per-button style.

### phase-1 — Error Screen

1. **PanelHeader** — the same shared header, subtitle "Errors".
2. **Reading** — the error rate for the selected window, in the same position the latency screen uses.
3. **SegmentedControl** — the same shared window selector, same three windows.
