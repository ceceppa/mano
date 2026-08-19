# Technical Specification

<!-- Present and current, so the existence filter would skip mano spec too.
     The phase adds no new technical territory: recording and layout playback
     are both already specified below. -->

## Stack

- The library and its examples build with the existing toolchain; no new
  external dependencies are planned.

## Example playback

- Layout playback is driven by the existing sequencer: a layout is shown, held
  for a duration, then replaced by the next.
- The per-layout hold duration is a single shared value, defined here, so every
  recorded output has the same cadence: **8 seconds**.

## Recording

- Recorded output is produced by the existing offline frame writer, which is
  already wired into the build and needs no changes for new example kinds.
