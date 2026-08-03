# Phase Brief — MotionKit — Phase 3

## Why This Phase

Library consumers need a concise target-bound authoring surface for ordinary motion without learning internal property paths.

## Phase Goal

Developers can create common target motions through `Motion.for(target)` and receive the same canonical property-motion result as the existing builder.

## Phase Scope

- Add target-bound opacity, relative movement, and arbitrary-property authoring.
- Preserve canonical playback and validation behavior.

## Exit Criteria

1. A developer authors each supported convenience motion and observes the expected target property change.
2. Invalid targets or property/value combinations fail before playback with actionable guidance.

