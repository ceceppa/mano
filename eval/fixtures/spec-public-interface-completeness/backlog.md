# Backlog — MotionKit

## Items

### Target-bound convenience contract
- **Type:** feature
- **Context:**
  `Motion.for(target: MotionTarget) -> BoundMotion`. `opacity(destination: number, durationSeconds?: number) -> PropertyMotion` maps to `style.opacity`; omitted duration remains inherited. `moveBy(offset: Point, durationSeconds?: number) -> PropertyMotion` maps relative movement to `position` captured at motion start.
  `property(path: string, destination: unknown, durationSeconds?: number) -> PropertyMotion` passes the supplied path through unchanged. All three delegate to the existing `CanonicalMotion` property builder rather than creating a second runtime.
  A null target is rejected as `target required`; unsupported target/property/value combinations return a validation failure before playback.
- **Status:** in-phase-3

### Deferred spring presets
- **Type:** feature
- **Context:**
  Add named spring presets in a later phase. This must never appear in the current technical specification.
- **Status:** backlog

### Unrelated logging convention
- **Type:** rule-gap
- **Context:**
  Decide how diagnostic logging is formatted. This belongs to mano rules and must not enter spec input.
- **Status:** backlog

