# Tech Spec — PulseKit

## Modules

- The latency screen is the CommonJS module `src/screens/latency-screen.js`, exporting a `render(service)` function that returns the screen's element tree.
- The error screen is the CommonJS module `src/screens/error-screen.js`, exporting a `render(service)` function with the same shape.
- Shared components live under `src/components/` and are required by the screens that use them. `PanelHeader` and `SegmentedControl` already exist there.

## Windows

- The selectable windows are `1h`, `24h`, and `7d`, in that order. `24h` is selected on first open of either screen.
- `service.latencyMs[window]` and `service.errorRate[window]` hold the value for each window.

## Out of Scope

- Persistence and remote fetching; a screen renders from the service object it is given.
