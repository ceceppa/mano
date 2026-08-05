# Phase Brief — RelayKit — Phase 4

## Why This Phase

Consumers need a small subscription facade for observing job status and progress without depending on transport details.

## Phase Goal

Developers can register handlers through `Relay.listen()` and receive status and progress updates through one shared event model.

## Phase Scope

- Add the `Relay.listen()` public subscription facade.
- Support status and progress notifications plus invalid-subscription feedback.

## Exit Criteria

1. A consumer subscribes, receives status and progress notifications, then unsubscribes.
2. An invalid subscription fails with actionable guidance.

