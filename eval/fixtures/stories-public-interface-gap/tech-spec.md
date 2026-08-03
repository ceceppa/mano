# Tech Spec — RelayKit

## Current Technical Summary

| | |
|---|---|
| Runtime / framework | Existing event library |
| Main interfaces | `Relay.listen()` facade |

## Subscription contract

`Relay.listen()` exposes convenient status and progress notifications using the canonical event model. It supports normal validation, cleanup, and failure handling.

## Key Technical Decisions

- The existing event transport remains unchanged.

