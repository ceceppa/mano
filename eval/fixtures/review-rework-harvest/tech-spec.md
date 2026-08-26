# Technical Specification — Preview Service

## Current Technical Summary

| Area | Decision |
|---|---|
| Runtime / framework | Application runtime, UI layer |
| Language | Application language |
| Testing | Standard test runner |

## Data Model

| Entity | Fields | Notes |
|---|---|---|
| `ThumbnailWatcher` | before and after rectangles, `properties`, playback state | Runtime-only record for one supported thumbnail layout change. `properties` is fixed to position and size; it never becomes serialized layout data. |

## Settling contract

Automatic settling applies only to thumbnails managed by one panel. A settle captures each thumbnail's rectangle before and after the layout engine performs its normal update. The engine's final rectangle remains authoritative; the service animates only the temporary visual difference.
