# Tech Spec — MotionKit

## Current Technical Summary

| | |
|---|---|
| Runtime / framework | Existing TypeScript motion library |
| Main interfaces | `CanonicalMotion`; planned `Motion.for()` convenience surface |

## Data Model

Serialized definitions use stable string IDs and never retain live target objects.

## Target-bound authoring

`Motion.for()` offers opacity, movement, and generic-property conveniences. Every convenience uses the canonical motion implementation and normal validation.

## Key Technical Decisions

- Playback remains driven by the existing scheduler.

