# Phase Brief — PulseKit — Phase 1

## Why This Phase

Operators can already see the service roster, but nothing shows how a single service is behaving over time. This phase adds the two per-service views they open from the roster.

## Phase Goal

An operator can inspect one service's latency and one service's error rate on their own screens.

## Phase Scope

1. **Per-service screens**
   a. **Latency screen** — an operator opens a service's latency screen and sees its latency for the selected window
   b. **Error screen** — an operator opens a service's error screen and sees its error rate for the selected window

## Not This Phase

- Alerting, thresholds, and any screen beyond the two named ones.
- Comparing two services side by side.

## Exit Criteria

1. **Per-service screens**
   a. Open the latency screen for a service and pick each window: the reported latency changes to that window's value
   b. Open the error screen for the same service and pick each window: the reported error rate changes to that window's value

## Acknowledged Risks

- None.
